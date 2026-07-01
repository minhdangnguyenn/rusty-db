#![warn(clippy::all)]

use std::collections::HashSet;
use std::fs::{File, create_dir_all};
use std::io::{BufWriter, Write as _};
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use clap::Parser;
use hdrhistogram::Histogram;
use itertools::Itertools as _;
use rand::RngExt as _;
use rand::SeedableRng as _;
use rand::distr::Distribution as _;
use rand::rngs::StdRng;
use rand::seq::SliceRandom as _;

use toydb::error::Result;
use toydb::sql::types::Value;
use toydb::{Client, StatementResult, cache, errdata};

fn latency_stats(hist: &Histogram<u32>) -> (f64, f64, f64, f64) {
    let p50_ms = Duration::from_nanos(hist.value_at_quantile(0.5)).as_secs_f64() * 1000.0;
    let p90_ms = Duration::from_nanos(hist.value_at_quantile(0.9)).as_secs_f64() * 1000.0;
    let p99_ms = Duration::from_nanos(hist.value_at_quantile(0.99)).as_secs_f64() * 1000.0;
    let max = Duration::from_nanos(hist.max()).as_secs_f64() * 1000.0;
    (p50_ms, p90_ms, p99_ms, max)
}

#[allow(clippy::too_many_arguments)]
fn log_stats(
    csv: &mut impl std::io::Write,
    duration_s: f64,
    progress: f64,
    txns: u64,
    throughput: f64,
    p50_ms: f64,
    p90_ms: f64,
    p99_ms: f64,
    max: f64,
    cache_hits: u64,
    cache_misses: u64,
    cache_hit_rate: f64,
) -> Result<()> {
    println!(
        "{:<8} {:>5.1}%  {:>7}  {:>6.0}/s  {:>6.1}ms  {:>6.1}ms  {:>6.1}ms  {:>6.1}ms  {:>7}  {:>7}  {:>5.1}%",
        format!("{:.1}s", duration_s),
        progress,
        txns,
        throughput,
        p50_ms,
        p90_ms,
        p99_ms,
        max,
        cache_hits,
        cache_misses,
        cache_hit_rate * 100.0,
    );
    writeln!(
        csv,
        "{:.3},{:.3},{},{:.3},{:.6},{:.6},{:.6},{:.6},{},{},{:.6}",
        duration_s,
        progress,
        txns,
        throughput,
        p50_ms,
        p90_ms,
        p99_ms,
        max,
        cache_hits,
        cache_misses,
        cache_hit_rate,
    )?;
    csv.flush()?;
    Ok(())
}

fn main() {
    let Command { runner, subcommand } = Command::parse();
    let result = match subcommand {
        Subcommand::Read(read) => runner.run(read),
    };
    if let Err(error) = result {
        eprintln!("Error: {error}")
    }
}

/// Handles command-line parsing.
#[derive(clap::Parser)]
#[command(about = "Runs toyDB workload benchmarks.", version, propagate_version = true)]
struct Command {
    #[command(flatten)]
    runner: Runner,

    #[command(subcommand)]
    subcommand: Subcommand,
}

#[derive(clap::Subcommand)]
enum Subcommand {
    Read(Read),
}

/// Runs a workload benchmark.
#[derive(clap::Args)]
struct Runner {
    /// Hosts to connect to (optionally with port number).
    #[arg(
        short = 'H',
        long,
        value_delimiter = ',',
        default_value = "localhost:9601,localhost:9602,localhost:9603,localhost:9604,localhost:9605"
    )]
    hosts: Vec<String>,

    /// Number of concurrent workers to spawn.
    #[arg(short, long, default_value = "16")]
    concurrency: usize,

    /// Number of transactions to execute.
    #[arg(short = 'n', long, default_value = "100000")] // 100_000
    count: usize,

    /// run for this many seconds (capped by --count)
    #[arg(long, default_value = "30")]
    duration: f64,

    /// Seed to use for random number generation.
    #[arg(short, long, default_value = "16791084677885396490")]
    seed: u64,

    /// Output directory for benchmark artifacts (CSV files).
    #[arg(long, default_value = "csv")]
    out_dir: PathBuf,

    /// Experiment name/tag used in output filenames (e.g., exp1-baseline-small).
    #[arg(long)]
    experiment: String,

    #[arg(long)]
    id: Option<u64>,
}

impl Runner {
    /// runs the specified workload.
    fn run<W: Workload>(self, workload: W) -> Result<()> {
        let mut rng = StdRng::seed_from_u64(self.seed);
        let mut client = Client::connect(&self.hosts[0])?;

        // ensure output directory exists.
        create_dir_all(&self.out_dir)?;

        // create a run id to avoid overwriting files.
        let id = if let Some(id) = self.id {
            id
        } else {
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_else(|_| Duration::from_secs(0))
                .as_millis() as u64
        };

        let csv_path = self.out_dir.join(format!("{}-{}.csv", self.experiment, id));
        let summary_path = self.out_dir.join(format!("{}-{}-summary.csv", self.experiment, id));

        // set up a histogram recording txn latencies as nanoseconds. The
        // buckets range from 0.001s to 10s.
        let mut hist = Histogram::<u32>::new_with_bounds(1_000, 10_000_000_000, 3)?.into_sync();

        // CSV writer for per-second stats.
        let mut csv = {
            let f = File::create(&csv_path)?;
            let mut w = BufWriter::new(f);
            writeln!(
                w,
                "time_s,progress,txns,throughput,p50_ms,p90_ms,p99_ms,max,cache_hits,cache_misses,cache_hit_rate"
            )?;
            w
        };

        // CSV writer for final one-row summary.
        let mut csv_summary = {
            let f = File::create(&summary_path)?;
            let mut w = BufWriter::new(f);
            writeln!(
                w,
                "experiment,run_id,workload,hosts,concurrency,count,seed,total_time_s,txns,throughput,p50_ms,p90_ms,p99_ms,max,cache_hits,cache_misses,cache_hit_rate,duration"
            )?;
            w
        };

        // Prepare the dataset.
        print!("Preparing initial dataset... ");
        std::io::stdout().flush()?;
        let start = Instant::now();
        workload.prepare(&mut client, &mut rng)?;
        println!("done ({:.3}s)", start.elapsed().as_secs_f64());
        println!("Running Workload !");

        let bench_start = Instant::now();
        cache::reset_stats();

        // Spawn workers, round robin across hosts.
        std::thread::scope(|s| -> Result<()> {
            print!("Spawning {} workers... ", self.concurrency);
            std::io::stdout().flush()?;
            let start = Instant::now();

            let (work_tx, work_rx) = crossbeam::channel::bounded(self.concurrency);
            let (done_tx, done_rx) = crossbeam::channel::bounded::<()>(0);

            for addr in self.hosts.iter().cycle().take(self.concurrency) {
                let mut client = Client::connect(addr)?;
                let mut recorder = hist.recorder();
                let work_rx = work_rx.clone();
                let done_tx = done_tx.clone();
                s.spawn(move || -> Result<()> {
                    while let Ok(item) = work_rx.recv() {
                        let start = Instant::now();
                        client.with_retry(|client| W::execute(client, &item))?;
                        recorder.record(start.elapsed().as_nanos() as u64)?;
                    }
                    drop(done_tx); // disconnects done_rx once all workers exit
                    Ok(())
                });
            }
            drop(done_tx); // drop local copy

            println!("done ({:.3}s)", start.elapsed().as_secs_f64());

            let stop = Arc::new(AtomicBool::new(false));

            // Spawn work generator.
            {
                println!("Running workload {}...", workload);
                let generator = workload.generate(rng)?;
                let stop = stop.clone();
                s.spawn(move || -> Result<()> {
                    for item in generator {
                        if stop.load(Ordering::Relaxed) {
                            break;
                        }
                        if work_tx.send(item).is_err() {
                            break;
                        }
                    }
                    Ok(())
                });
            }

            // Periodically print stats until all workers are done.
            let start = Instant::now();
            let deadline = Instant::now() + Duration::from_secs_f64(self.duration);
            let ticker = crossbeam::channel::tick(Duration::from_secs(1));

            println!();
            println!(
                "Time   Progress     Txns      Rate       p50       p90       p99      max     hits    misses   hit%"
            );

            while let Err(crossbeam::channel::TryRecvError::Empty) = done_rx.try_recv() {
                crossbeam::select! {
                    recv(ticker) -> _ => {},
                    recv(done_rx) -> _ => break,
                }

                let duration_s = start.elapsed().as_secs_f64();
                hist.refresh_timeout(Duration::from_secs(1));

                let progress = (duration_s / self.duration * 100.0).min(100.0);
                let txns = hist.len();
                let throughput = hist.len() as f64 / duration_s;

                let (p50_ms, p90_ms, p99_ms, max) = latency_stats(&hist);
                let (cache_hits, cache_misses, cache_hit_rate) = cache::stats();

                log_stats(
                    &mut csv,
                    duration_s,
                    progress,
                    txns,
                    throughput,
                    p50_ms,
                    p90_ms,
                    p99_ms,
                    max,
                    cache_hits,
                    cache_misses,
                    cache_hit_rate,
                )?;

                if Instant::now() >= deadline {
                    stop.store(true, Ordering::Relaxed);
                    break;
                }
            }
            Ok(())
        })?;
        csv.flush()?; // flush any remaining csv data

        // Write one-row CSV summary.
        let total_time_s = bench_start.elapsed().as_secs_f64();
        hist.refresh_timeout(Duration::from_secs(0)); // refresh final snapshot

        let txns = hist.len();
        let throughput = txns as f64 / total_time_s;

        let (p50_ms, p90_ms, p99_ms, max) = latency_stats(&hist);

        let hosts = self.hosts.join(";");

        let (cache_hits, cache_misses, cache_hit_rate) = cache::stats();
        writeln!(
            csv_summary,
            "\"{}\",{},{:?},\"{}\",{},{},{},{:.3},{},{:.3},{:.6},{:.6},{:.6},{:.6},{},{},{:.6},{:.1}",
            self.experiment,
            id,
            workload.to_string(),
            hosts,
            self.concurrency,
            self.count,
            self.seed,
            total_time_s,
            txns,
            throughput,
            p50_ms,
            p90_ms,
            p99_ms,
            max,
            cache_hits,
            cache_misses,
            cache_hit_rate,
            self.duration,
        )?;
        csv_summary.flush()?;

        // Verify the final dataset.
        println!();
        print!("Verifying dataset... ");
        std::io::stdout().flush()?;
        let start = Instant::now();
        workload.verify(&mut client, self.count)?;
        println!("done ({:.3}s)", start.elapsed().as_secs_f64());

        Ok(())
    }
}

/// A workload.
trait Workload: std::fmt::Display {
    /// A work item.
    type Item: Send;

    /// Prepares the workload by creating initial tables and data.
    fn prepare(&self, client: &mut Client, rng: &mut StdRng) -> Result<()>;

    /// Generates work items as an iterator.
    fn generate(&self, rng: StdRng) -> Result<impl Iterator<Item = Self::Item> + Send + 'static>;

    /// Executes a single work item. This will automatically be retried on
    /// certain errors, and must use a transaction where appropriate.
    fn execute(client: &mut Client, item: &Self::Item) -> Result<()>;

    /// Verifies the dataset after the workload has completed.
    fn verify(&self, _client: &mut Client, _txns: usize) -> Result<()> {
        Ok(())
    }
}

/// A read-only workload. Creates an id,value table and populates it with the
/// given row count and value size. Then runs batches of random primary key
/// lookups (SELECT * FROM read WHERE id = 1 OR id = 2 ...).
#[derive(clap::Args, Clone)]
#[command(about = "A read-only workload using primary key lookups")]
struct Read {
    /// Total number of rows in data set.
    #[arg(short, long, default_value = "1000")]
    rows: u64,

    /// Row value size (excluding primary key).
    #[arg(short, long, default_value = "64")]
    size: usize,

    /// Number of rows to fetch in a single select.
    #[arg(short, long, default_value = "1")]
    batch: usize,

    /// block size for unique/repeated key pattern
    #[arg(long, default_value = "100")]
    block_size: usize,

    #[arg(long, default_value = "uniform")]
    dist: String,

    /// zipf skew parameter (only used with --dist zipf)
    #[arg(long, default_value = "1.0")] // 1.0: highly skewd
    zipf_skew: f64,

    /// enable cache or not
    #[arg(long)]
    cache: bool,

    #[arg(long)]
    fifo: bool,

    /// Maximum number of entries in cache.
    #[arg(long, default_value = "5000")]
    cache_size: usize,
}

impl std::fmt::Display for Read {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "read (rows={} size={} batch={} block={} distr={})",
            self.rows, self.size, self.batch, self.block_size, self.dist
        )
    }
}

impl Workload for Read {
    type Item = HashSet<u64>;

    fn prepare(&self, client: &mut Client, rng: &mut StdRng) -> Result<()> {
        if self.cache {
            cache::enable();
            cache::set_max_size(self.cache_size);
        }
        if self.fifo {
            cache::set_eviction(cache::EvictType::FIFO);
        }
        client.execute("BEGIN")?;
        client.execute(r#"DROP TABLE IF EXISTS "read""#)?;
        client.execute(r#"CREATE TABLE "read" (id INT PRIMARY KEY, value STRING NOT NULL)"#)?;

        let chars = &mut rand::distr::Alphanumeric.sample_iter(rng).map(|b| b as char);
        let rows = (1..=self.rows).map(|id| (id, chars.take(self.size).collect::<String>()));
        let chunks = rows.chunks(100);
        let queries = chunks.into_iter().map(|chunk| {
            format!(
                r#"INSERT INTO "read" (id, value) VALUES ({})"#,
                chunk.map(|(id, value)| format!("{}, '{}'", id, value)).join("), (")
            )
        });
        for query in queries {
            client.execute(&query)?;
        }
        client.execute("COMMIT")?;
        Ok(())
    }

    fn generate(&self, mut rng: StdRng) -> Result<impl Iterator<Item = Self::Item> + 'static> {
        let mut unseen: Vec<u64> = (1..=self.rows).collect();
        unseen.shuffle(&mut rng);
        Ok(BlockReadGenerator {
            batch: self.batch,
            block_size: self.block_size,
            rng,
            unseen,
            unseen_idx: 0,
            seen: Vec::with_capacity(self.rows as usize),
            keys_remaining: self.block_size,
            is_unique_block: true,
        })
    }

    // start running the workload
    fn execute(client: &mut Client, item: &Self::Item) -> Result<()> {
        let batch_size = item.len();

        // filter out cached IDs — query DB only for uncached
        let uncached_ids = cache::filter_uncached(item);
        let cached_count = batch_size - uncached_ids.len();

        if !uncached_ids.is_empty() {
            let query = format!(
                r#"SELECT id, value FROM "read" WHERE {}"#,
                uncached_ids.iter().map(|id| format!("id = {id}")).join(" OR ")
            );
            let result = client.execute(&query)?;
            let StatementResult::Select { rows, .. } = result else {
                return errdata!("expected select result, found {result:?}");
            };
            for row in &rows {
                // row[0] = id (Integer), row[1] = value (String)
                if let (Value::Integer(id), Value::String(value)) = (&row[0], &row[1]) {
                    // add query result into cache
                    cache::insert(*id as u64, value.clone());
                }
            }
            assert_eq!(rows.len() + cached_count, batch_size, "Unexpected row count");
        } else {
            // All IDs were cached — nothing to query
            assert_eq!(cached_count, batch_size, "All IDs should be cached");
        }
        Ok(())
    }

    fn verify(&self, client: &mut Client, _: usize) -> Result<()> {
        let count: i64 = client.execute(r#"SELECT COUNT(*) FROM "read""#)?.try_into()?;
        assert_eq!(count, self.rows as i64, "Unexpected row count");
        Ok(())
    }
}

/// key generator that alternates unique and repeated blocks.
/// each unique block generates fresh keys not seen before.
/// each repeated block samples randomly from keys seen so far.
struct BlockReadGenerator {
    batch: usize,
    block_size: usize,
    rng: StdRng,
    unseen: Vec<u64>,
    unseen_idx: usize,
    seen: Vec<u64>,
    keys_remaining: usize,
    is_unique_block: bool,
}

impl Iterator for BlockReadGenerator {
    type Item = <Read as Workload>::Item;

    fn next(&mut self) -> Option<Self::Item> {
        if self.keys_remaining == 0 {
            self.is_unique_block = !self.is_unique_block;
            self.keys_remaining = self.block_size;
        }

        let n = self.batch.min(self.keys_remaining);
        self.keys_remaining -= n;

        let mut ids = HashSet::new();
        if self.is_unique_block {
            for _ in 0..n {
                if self.unseen_idx < self.unseen.len() {
                    let id = self.unseen[self.unseen_idx];
                    self.unseen_idx += 1;
                    self.seen.push(id);
                    ids.insert(id);
                } else {
                    // all keys seen — fall back to sampling from seen
                    let i = self.rng.random_range(0..self.seen.len());
                    ids.insert(self.seen[i]);
                }
            }
        } else {
            for _ in 0..n {
                let i = self.rng.random_range(0..self.seen.len());
                ids.insert(self.seen[i]);
            }
        }
        Some(ids)
    }
}
