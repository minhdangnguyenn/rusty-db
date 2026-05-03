use std::cmp::min;

use itertools::Itertools as _;
use rand::distr::Distribution as _;
use rand::rngs::StdRng;
use rand::seq::IndexedRandom as _;

use toydb::Client;
use toydb::error::Result;
use toydb::sql::types::Row;

use super::Workload;

/// A bank workload, making transfers between customer accounts.
#[derive(clap::Args, Clone)]
#[command(about = "A bank workload, making transfers between customer accounts")]
pub struct Bank {
    /// Number of customers.
    #[arg(short, long, default_value = "100")]
    customers: u64,

    /// Number of accounts per customer.
    #[arg(short, long, default_value = "10")]
    accounts: u64,

    /// Initial account balance.
    #[arg(short, long, default_value = "100")]
    balance: u64,

    /// Max amount to transfer.
    #[arg(short, long, default_value = "50")]
    max_transfer: u64,
}

impl std::fmt::Display for Bank {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "bank (customers={} accounts={})", self.customers, self.accounts)
    }
}

impl Workload for Bank {
    type Item = (u64, u64, u64); // from,to,amount

    fn prepare(&self, client: &mut Client, rng: &mut StdRng) -> Result<()> {
        let petnames = petname::Petnames::default();
        client.execute("BEGIN")?;
        client.execute("DROP TABLE IF EXISTS account")?;
        client.execute("DROP TABLE IF EXISTS customer")?;
        client.execute(
            "CREATE TABLE customer (
                    id INTEGER PRIMARY KEY,
                    name STRING NOT NULL
                )",
        )?;
        client.execute(
            "CREATE TABLE account (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL INDEX REFERENCES customer,
                    balance INTEGER NOT NULL
                )",
        )?;
        client.execute(&format!(
            "INSERT INTO customer VALUES {}",
            (1..=self.customers)
                .map(|id| {
                    let name = [
                        *petnames.adverbs.choose(rng).expect("no adverb"),
                        *petnames.adjectives.choose(rng).expect("no adjective"),
                        *petnames.nouns.choose(rng).expect("no noun"),
                    ]
                    .join(" ");
                    (id, name)
                })
                .map(|(id, name)| format!("({}, '{}')", id, name))
                .join(", ")
        ))?;
        client.execute(&format!(
            "INSERT INTO account VALUES {}",
            (1..=self.customers)
                .flat_map(|c| (1..=self.accounts).map(move |a| (c, (c - 1) * self.accounts + a)))
                .map(|(c, a)| format!("({}, {}, {})", a, c, self.balance))
                .join(", ")
        ))?;
        client.execute("COMMIT")?;
        Ok(())
    }

    fn generate(&self, rng: StdRng) -> Result<impl Iterator<Item = Self::Item> + 'static> {
        let customers = self.customers;
        let max_transfer = self.max_transfer;
        Ok(rand::distr::Uniform::new_inclusive(0, u64::MAX)?
            .sample_iter(rng)
            .tuples()
            .map(move |(a, b, c)| (a % customers + 1, b % customers + 1, c % max_transfer + 1))
            .filter(|(from, to, _)| from != to))
    }

    fn execute(client: &mut Client, item: &Self::Item) -> Result<()> {
        let &(from, to, mut amount) = item;

        client.execute("BEGIN")?;

        let row: Row = client
            .execute(&format!(
                "SELECT a.id, a.balance
                        FROM account a JOIN customer c ON a.customer_id = c.id
                        WHERE c.id = {}
                        ORDER BY a.balance DESC
                        LIMIT 1",
                from
            ))?
            .try_into()?;
        let mut row = row.into_iter();
        let from_account: i64 = row.next().unwrap().try_into()?;
        let from_balance: i64 = row.next().unwrap().try_into()?;
        amount = min(amount, from_balance as u64);

        let to_account: i64 = client
            .execute(&format!(
                "SELECT a.id, a.balance
                        FROM account a JOIN customer c ON a.customer_id = c.id
                        WHERE c.id = {}
                        ORDER BY a.balance ASC
                        LIMIT 1",
                to
            ))?
            .try_into()?;

        client.execute(&format!(
            "UPDATE account SET balance = balance - {} WHERE id = {}",
            amount, from_account,
        ))?;
        client.execute(&format!(
            "UPDATE account SET balance = balance + {} WHERE id = {}",
            amount, to_account,
        ))?;

        client.execute("COMMIT")?;

        Ok(())
    }

    fn verify(&self, client: &mut Client, _: usize) -> Result<()> {
        let balance: i64 = client.execute("SELECT SUM(balance) FROM account")?.try_into()?;
        assert_eq!(balance as u64, self.customers * self.accounts * self.balance);
        let negative: i64 =
            client.execute("SELECT COUNT(*) FROM account WHERE balance < 0")?.try_into()?;
        assert_eq!(negative, 0);
        Ok(())
    }
}
