use itertools::Itertools as _;
use rand::distr::Distribution as _;
use rand::rngs::StdRng;

use toydb::Client;
use toydb::error::Result;
use toydb::sql::types::Rows;

use super::Workload;

/// Range-scan workload over the PRIMARY KEY (default B-tree ordering).
#[derive(clap::Args, Clone)]
#[command(about = "A range-scan workload using primary key range predicates")]
pub struct Range {
    /// Total number of rows in data set.
    #[arg(short, long, default_value = "1000000")]
    rows: u64,

    /// Row value size (excluding primary key).
    #[arg(short, long, default_value = "64")]
    size: usize,

    /// Number of rows returned per query (controls selectivity).
    #[arg(short, long, default_value = "100")]
    width: u64,
}

impl std::fmt::Display for Range {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "range (rows={} size={} width={})", self.rows, self.size, self.width)
    }
}

impl Workload for Range {
    type Item = (u64, u64); // (start,end)

    fn prepare(&self, client: &mut Client, rng: &mut StdRng) -> Result<()> {
        client.execute("BEGIN")?;
        client.execute(r#"DROP TABLE IF EXISTS "range""#)?;
        client.execute(r#"CREATE TABLE "range" (id INT PRIMARY KEY, value STRING NOT NULL)"#)?;

        let chars = &mut rand::distr::Alphanumeric.sample_iter(rng).map(|b| b as char);
        let rows = (1..=self.rows).map(|id| (id, chars.take(self.size).collect::<String>()));
        let chunks = rows.chunks(100);

        for chunk in chunks.into_iter() {
            let query = format!(
                r#"INSERT INTO "range" (id, value) VALUES ({})"#,
                chunk.map(|(id, value)| format!("{}, '{}'", id, value)).join("), (")
            );
            client.execute(&query)?;
        }

        client.execute("COMMIT")?;
        Ok(())
    }

    fn generate(&self, rng: StdRng) -> Result<impl Iterator<Item = Self::Item> + Send + 'static> {
        Ok(RangeGenerator {
            rng,
            rows: self.rows,
            width: self.width.max(1).min(self.rows),
            dist: rand::distr::Uniform::new(1, self.rows + 1)?,
        })
    }

    fn execute(client: &mut Client, item: &Self::Item) -> Result<()> {
        let (start, end) = *item;
        let query = format!(r#"SELECT * FROM "range" WHERE id >= {} AND id < {}"#, start, end);
        let rows: Rows = client.execute(&query)?.try_into()?;
        assert_eq!(rows.count(), (end - start) as usize, "Unexpected row count");
        Ok(())
    }

    fn verify(&self, client: &mut Client, _: usize) -> Result<()> {
        let count: i64 = client.execute(r#"SELECT COUNT(*) FROM "range""#)?.try_into()?;
        assert_eq!(count as u64, self.rows, "Unexpected row count");
        Ok(())
    }
}

struct RangeGenerator {
    rng: StdRng,
    rows: u64,
    width: u64,
    dist: rand::distr::Uniform<u64>,
}

impl Iterator for RangeGenerator {
    type Item = (u64, u64);

    fn next(&mut self) -> Option<Self::Item> {
        let start = self.dist.sample(&mut self.rng);
        let start = start.min(self.rows.saturating_sub(self.width) + 1);
        let end = start + self.width;
        Some((start, end))
    }
}
