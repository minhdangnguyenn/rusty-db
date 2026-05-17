//! Runs toyDB workload benchmarks. By default, it assumes a running 5-node
//! cluster as launched via cluster/run.sh, but this can be modified via -H.
//! For example, a read-only workload can be run as:
//!
//! cargo run --release --bin workload -- read
//!
//! See --help for a list of available workloads and arguments.

#![warn(clippy::all)]

mod workloads;

use std::fs::{File, create_dir_all};
use std::io::{BufWriter, Write as _};
use std::path::PathBuf;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use clap::Parser;
use hdrhistogram::Histogram;
use rand::SeedableRng as _;
use rand::rngs::StdRng;

use toydb::Client;
use toydb::error::Result;

use workloads::{Bank, Range, Read, Workload, Write};

fn main() {
    let Command { runner, subcommand } = Command::parse();
    let result = match subcommand {
        Subcommand::Read(read) => runner.run(read),
        Subcommand::Write(write) => runner.run(write),
        Subcommand::Bank(bank) => runner.run(bank),
        Subcommand::Range(range) => runner.run(range),
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
    Write(Write),
    Bank(Bank),
    Range(Range),
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
    #[arg(short = 'n', long, default_value = "100000")]
    count: usize,

    /// Seed to use for random number generation.
    #[arg(short, long, default_value = "16791084677885396490")]
    seed: u64,

    /// Output directory for benchmark artifacts (CSV files).
    #[arg(long, default_value = "csv")]
    out_dir: PathBuf,

    /// Experiment name/tag used in output filenames (e.g., exp1-baseline-small).
    #[arg(long)]
    experiment: String,
}

impl Runner {
    /// Runs the specified workload.
    fn run<W: Workload>(self, workload: W) -> Result<()> {
        let mut rng = StdRng::seed_from_u64(self.seed);
        let mut client = Client::connect(&self.hosts[0])?;

        // Ensure output directory exists.
        create_dir_all(&self.out_dir)?;

        // Create a run id to avoid overwriting files.
        let run_id = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_else(|_| Duration::from_secs(0))
            .as_millis();

        let csv_path = self.out_dir.join(format!("{}-{}.csv", self.experiment, run_id));
        let summary_path = self.out_dir.join(format!("{}-{}-summary.csv", self.experiment, run_id));

        // Set up a histogram recording txn latencies as nanoseconds. The
        // buckets range from 0.001s to 10s.
        let mut hist = Histogram::<u32>::new_with_bounds(1_000, 10_000_000_000, 3)?.into_sync();

        // CSV writer for per-second stats.
        let mut csv = {
            let f = File::create(&csv_path)?;
            let mut w = BufWriter::new(f);
            writeln!(w, "time_s,progress,txns,rate_tps,p50_ms,p90_ms,p99_ms,max_ms")?;
            w
        };

        // CSV writer for final one-row summary.
        let mut csv_summary = {
            let f = File::create(&summary_path)?;
            let mut w = BufWriter::new(f);
            writeln!(
                w,
                "experiment,run_id,workload,hosts,concurrency,count,seed,total_time_s,txns,rate_tps,p50_ms,p90_ms,p99_ms,max_ms"
            )?;
            w
        };

        // Prepare the dataset.
        print!("Preparing initial dataset... ");
        std::io::stdout().flush()?;
        let start = Instant::now();
        workload.prepare(&mut client, &mut rng)?;
        println!("Prepare Initial Dataset done ({:.3}s)", start.elapsed().as_secs_f64());
        println!("Running Workload !");

        let bench_start = Instant::now();

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

            // Spawn work generator.
            {
                println!("Running workload {}...", workload);
                let generator = workload.generate(rng)?.take(self.count);
                s.spawn(move || -> Result<()> {
                    for item in generator {
                        work_tx.send(item)?;
                    }
                    Ok(())
                });
            }

            // Periodically print stats until all workers are done.
            let start = Instant::now();
            let ticker = crossbeam::channel::tick(Duration::from_secs(1));

            println!();
            println!("Time   Progress     Txns      Rate       p50       p90       p99      max");

            while let Err(crossbeam::channel::TryRecvError::Empty) = done_rx.try_recv() {
                crossbeam::select! {
                    recv(ticker) -> _ => {},
                    recv(done_rx) -> _ => {},
                }

                let duration_s = start.elapsed().as_secs_f64();
                hist.refresh_timeout(Duration::from_secs(1));

                let progress = hist.len() as f64 / self.count as f64 * 100.0;
                let txns = hist.len();
                let rate_tps = hist.len() as f64 / duration_s;

                let p50_ms =
                    Duration::from_nanos(hist.value_at_quantile(0.5)).as_secs_f64() * 1000.0;
                let p90_ms =
                    Duration::from_nanos(hist.value_at_quantile(0.9)).as_secs_f64() * 1000.0;
                let p99_ms =
                    Duration::from_nanos(hist.value_at_quantile(0.99)).as_secs_f64() * 1000.0;
                let max_ms = Duration::from_nanos(hist.max()).as_secs_f64() * 1000.0;

                println!(
                    "{:<8} {:>5.1}%  {:>7}  {:>6.0}/s  {:>6.1}ms  {:>6.1}ms  {:>6.1}ms  {:>6.1}ms",
                    format!("{:.1}s", duration_s),
                    progress,
                    txns,
                    rate_tps,
                    p50_ms,
                    p90_ms,
                    p99_ms,
                    max_ms,
                );

                writeln!(
                    csv,
                    "{:.3},{:.3},{},{:.3},{:.6},{:.6},{:.6},{:.6}",
                    duration_s, progress, txns, rate_tps, p50_ms, p90_ms, p99_ms, max_ms,
                )?;
                csv.flush()?; // keep data even if benchmark aborts
            }
            Ok(())
        })?;

        // Write one-row CSV summary.
        let total_time_s = bench_start.elapsed().as_secs_f64();
        hist.refresh_timeout(Duration::from_secs(0)); // refresh final snapshot

        let txns = hist.len();
        let rate_tps = txns as f64 / total_time_s;

        let p50_ms = Duration::from_nanos(hist.value_at_quantile(0.5)).as_secs_f64() * 1000.0;
        let p90_ms = Duration::from_nanos(hist.value_at_quantile(0.9)).as_secs_f64() * 1000.0;
        let p99_ms = Duration::from_nanos(hist.value_at_quantile(0.99)).as_secs_f64() * 1000.0;
        let max_ms = Duration::from_nanos(hist.max()).as_secs_f64() * 1000.0;

        let hosts = self.hosts.join(";");

        writeln!(
            csv_summary,
            "\"{}\",{},{:?},\"{}\",{},{},{},{:.3},{},{:.3},{:.6},{:.6},{:.6},{:.6}",
            self.experiment,
            run_id,
            workload.to_string(),
            hosts,
            self.concurrency,
            self.count,
            self.seed,
            total_time_s,
            txns,
            rate_tps,
            p50_ms,
            p90_ms,
            p99_ms,
            max_ms,
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
