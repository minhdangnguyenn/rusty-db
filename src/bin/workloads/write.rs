use itertools::Itertools as _;
use rand::rngs::StdRng;

use rand::distr::Distribution as _;
use toydb::Client;
use toydb::StatementResult;
use toydb::error::Result;

use super::Workload;

/// A write-only workload. Creates an id,value table, and writes rows with
/// sequential primary keys and the given value size, in the given batch size
/// (INSERT INTO write (id, value) VALUES ...). The number of rows written
/// is given by Runner.count * Write.batch.
#[derive(clap::Args, Clone)]
#[command(about = "A write-only workload writing sequential rows")]
pub struct Write {
    /// Row value size (excluding primary key).
    #[arg(short, long, default_value = "64")]
    size: usize,

    /// Number of rows to write in a single insert query.
    #[arg(short, long, default_value = "1")]
    batch: usize,
}

impl std::fmt::Display for Write {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "write (size={} batch={})", self.size, self.batch)
    }
}

impl Workload for Write {
    type Item = Vec<(u64, String)>;

    fn prepare(&self, client: &mut Client, _: &mut StdRng) -> Result<()> {
        client.execute("BEGIN")?;
        client.execute(r#"DROP TABLE IF EXISTS "write""#)?;
        client.execute(r#"CREATE TABLE "write" (id INT PRIMARY KEY, value STRING NOT NULL)"#)?;
        client.execute("COMMIT")?;
        Ok(())
    }

    fn generate(&self, rng: StdRng) -> Result<impl Iterator<Item = Self::Item> + 'static> {
        Ok(WriteGenerator { next_id: 1, size: self.size, batch: self.batch, rng })
    }

    fn execute(client: &mut Client, item: &Self::Item) -> Result<()> {
        let batch_size = item.len();
        let query = format!(
            r#"INSERT INTO "write" (id, value) VALUES {}"#,
            item.iter().map(|(id, value)| format!("({}, '{}')", id, value)).join(", ")
        );
        if let StatementResult::Insert { count } = client.execute(&query)? {
            assert_eq!(count as usize, batch_size, "Unexpected row count");
        } else {
            panic!("Unexpected result")
        }
        Ok(())
    }

    fn verify(&self, client: &mut Client, txns: usize) -> Result<()> {
        let count: i64 = client.execute(r#"SELECT COUNT(*) FROM "write""#)?.try_into()?;
        assert_eq!(count as usize, txns * self.batch, "Unexpected row count");
        Ok(())
    }
}

/// A Write workload generator, yielding batches of sequential primary keys and
/// random rows.
struct WriteGenerator {
    next_id: u64,
    size: usize,
    batch: usize,
    rng: StdRng,
}

impl Iterator for WriteGenerator {
    type Item = <Write as Workload>::Item;

    fn next(&mut self) -> Option<Self::Item> {
        let chars = &mut rand::distr::Alphanumeric.sample_iter(&mut self.rng).map(|b| b as char);
        let mut rows = Vec::with_capacity(self.batch);
        while rows.len() < self.batch {
            rows.push((self.next_id, chars.take(self.size).collect()));
            self.next_id += 1;
        }
        Some(rows)
    }
}
