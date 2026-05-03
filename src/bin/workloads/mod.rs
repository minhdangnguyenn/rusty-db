#![allow(clippy::module_name_repetitions)]

mod bank;
mod range;
mod read;
mod write;

pub use bank::Bank;
pub use range::Range;
pub use read::Read;
pub use write::Write;

use rand::rngs::StdRng;
use toydb::Client;
use toydb::error::Result;

/// A workload.
pub trait Workload: std::fmt::Display {
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
