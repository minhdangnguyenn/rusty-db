use std::collections::HashSet;

use itertools::Itertools as _;
use rand::distr::Distribution as _;
use rand::rngs::StdRng;

use toydb::Client;
use toydb::error::Result;
use toydb::sql::types::Rows;

use super::Workload;

/// A read-only workload. Creates an id,value table and populates it with the
/// given row count and value size. Then runs batches of random primary key
/// lookups (SELECT * FROM read WHERE id = 1 OR id = 2 ...).
#[derive(clap::Args, Clone)]
#[command(about = "A read-only workload using primary key lookups")]
pub struct Read {
    /// Total number of rows in data set.
    #[arg(short, long, default_value = "1000")]
    rows: u64,

    /// Row value size (excluding primary key).
    #[arg(short, long, default_value = "64")]
    size: usize,

    /// Number of rows to fetch in a single select.
    #[arg(short, long, default_value = "1")]
    batch: usize,
}

impl std::fmt::Display for Read {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "read (rows={} size={} batch={})", self.rows, self.size, self.batch)
    }
}

impl Workload for Read {
    type Item = HashSet<u64>;

    fn prepare(&self, client: &mut Client, rng: &mut StdRng) -> Result<()> {
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

    fn generate(&self, rng: StdRng) -> Result<impl Iterator<Item = Self::Item> + 'static> {
        Ok(ReadGenerator {
            batch: self.batch,
            dist: rand::distr::Uniform::new(1, self.rows + 1)?,
            rng,
        })
    }

    fn execute(client: &mut Client, item: &Self::Item) -> Result<()> {
        let batch_size = item.len();
        let query = format!(
            r#"SELECT * FROM "read" WHERE {}"#,
            item.iter().map(|id| format!("id = {}", id)).join(" OR ")
        );
        let rows: Rows = client.execute(&query)?.try_into()?;
        assert_eq!(rows.count(), batch_size, "Unexpected row count");
        Ok(())
    }

    fn verify(&self, client: &mut Client, _: usize) -> Result<()> {
        let count: i64 = client.execute(r#"SELECT COUNT(*) FROM "read""#)?.try_into()?;
        assert_eq!(count, self.rows as i64, "Unexpected row count");
        Ok(())
    }
}

/// A Read workload generator, yielding batches of random, unique primary keys.
struct ReadGenerator {
    batch: usize,
    rng: StdRng,
    dist: rand::distr::Uniform<u64>,
}

impl Iterator for ReadGenerator {
    type Item = <Read as Workload>::Item;

    fn next(&mut self) -> Option<Self::Item> {
        let mut ids = HashSet::new();
        for id in self.dist.sample_iter(&mut self.rng) {
            ids.insert(id);
            if ids.len() >= self.batch {
                break;
            }
        }
        Some(ids)
    }
}
