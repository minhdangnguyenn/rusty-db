# <a><img src="./docs/architecture/images/toydb.svg" height="40" valign="top" /></a> RustyDB, based on toyDB

Distributed SQL database in Rust, built from scratch as an educational project. Main features:

- [Raft distributed consensus][raft] for linearizable state machine replication.

- [ACID transactions][txn] with MVCC-based snapshot isolation.

- [Pluggable storage engine][storage] with [BitCask][bitcask] and [in-memory][memory] backends.

- [Iterator-based query engine][query] with [heuristic optimization][optimizer] and time-travel
  support.

- [SQL interface][sql] including joins, aggregates, and transactions.

toyDB is intended to be simple and understandable, and also functional and correct. Other aspects
like performance, scalability, and availability are non-goals -- these are major sources of
complexity in production-grade databases, and obscure the basic underlying concepts. Shortcuts have
been taken where possible.

I originally wrote toyDB in 2020 to learn more about database internals. Since then, I've spent
several years building real distributed SQL databases at
[CockroachDB](https://github.com/cockroachdb/cockroach) and
[Neon](https://github.com/neondatabase/neon). Based on this experience, I've rewritten toyDB as a
simple illustration of the architecture and concepts behind distributed SQL databases.

[raft]: https://github.com/erikgrinaker/toydb/blob/main/src/raft/mod.rs
[txn]: https://github.com/erikgrinaker/toydb/blob/main/src/storage/mvcc.rs
[storage]: https://github.com/erikgrinaker/toydb/blob/main/src/storage/engine.rs
[bitcask]: https://github.com/erikgrinaker/toydb/blob/main/src/storage/bitcask.rs
[memory]: https://github.com/erikgrinaker/toydb/blob/main/src/storage/memory.rs
[query]: https://github.com/erikgrinaker/toydb/blob/main/src/sql/execution/executor.rs
[optimizer]: https://github.com/erikgrinaker/toydb/blob/main/src/sql/planner/optimizer.rs
[sql]: https://github.com/erikgrinaker/toydb/blob/main/src/sql/parser/parser.rs

## Documentation

- [Architecture guide](docs/architecture/index.md): a guided tour of toyDB's code and architecture.

- [SQL examples](docs/examples.md): walkthrough of toyDB's SQL features.

- [SQL reference](docs/sql.md): reference documentation for toyDB's SQL dialect.

- [References](docs/references.md): research materials used while building toyDB.

## Usage

With a [Rust compiler](https://www.rust-lang.org/tools/install) installed, a local five-node
cluster can be built and started as:

```
$ ./cluster/run.sh
Starting 5 nodes on ports 9601-9605 with data under cluster/*/data/.
To connect to node 1, run: cargo run --release --bin toysql

toydb4 21:03:55 [INFO] Listening on [::1]:9604 (SQL) and [::1]:9704 (Raft)
toydb1 21:03:55 [INFO] Listening on [::1]:9601 (SQL) and [::1]:9701 (Raft)
toydb2 21:03:55 [INFO] Listening on [::1]:9602 (SQL) and [::1]:9702 (Raft)
toydb3 21:03:55 [INFO] Listening on [::1]:9603 (SQL) and [::1]:9703 (Raft)
toydb5 21:03:55 [INFO] Listening on [::1]:9605 (SQL) and [::1]:9705 (Raft)
toydb2 21:03:56 [INFO] Starting new election for term 1
[...]
toydb2 21:03:56 [INFO] Won election for term 1, becoming leader
```

A command-line client can be built and used with node 1 on `localhost:9601`:

```
$ cargo run --release --bin toysql
Connected to toyDB node n1. Enter !help for instructions.
toydb> CREATE TABLE movies (id INTEGER PRIMARY KEY, title VARCHAR NOT NULL);
toydb> INSERT INTO movies VALUES (1, 'Sicario'), (2, 'Stalker'), (3, 'Her');
toydb> SELECT * FROM movies;
1, 'Sicario'
2, 'Stalker'
3, 'Her'
```

toyDB supports most common SQL features, including joins, aggregates, and transactions. Below is an
`EXPLAIN` query plan of a more complex query (fetches all movies from studios that have released any
movie with an IMDb rating of 8 or more):

```
toydb> EXPLAIN SELECT m.title, g.name AS genre, s.name AS studio, m.rating
  FROM movies m JOIN genres g ON m.genre_id = g.id,
    studios s JOIN movies good ON good.studio_id = s.id AND good.rating >= 8
  WHERE m.studio_id = s.id
  GROUP BY m.title, g.name, s.name, m.rating, m.released
  ORDER BY m.rating DESC, m.released ASC, m.title ASC;

Remap: m.title, genre, studio, m.rating (dropped: m.released)
└─ Order: m.rating desc, m.released asc, m.title asc
   └─ Projection: m.title, g.name as genre, s.name as studio, m.rating, m.released
      └─ Aggregate: m.title, g.name, s.name, m.rating, m.released
         └─ HashJoin: inner on m.studio_id = s.id
            ├─ HashJoin: inner on m.genre_id = g.id
            │  ├─ Scan: movies as m
            │  └─ Scan: genres as g
            └─ HashJoin: inner on s.id = good.studio_id
               ├─ Scan: studios as s
               └─ Scan: movies as good (good.rating > 8 OR good.rating = 8)
```

## Architecture

toyDB's architecture is fairly typical for a distributed SQL database: a transactional
key/value store managed by a Raft cluster with a SQL query engine on top. See the
[architecture guide](./docs/architecture/index.md) for more details.

[![toyDB architecture](./docs/architecture/images/architecture.svg)](./docs/architecture/index.md)

## Tests

toyDB mainly uses [Goldenscripts](https://github.com/erikgrinaker/goldenscript) for tests. These
script various scenarios, capture events and output, and later assert that the behavior remains the
same. See e.g.:

- [Raft cluster tests](https://github.com/erikgrinaker/toydb/tree/main/src/raft/testscripts/node)
- [MVCC transaction tests](https://github.com/erikgrinaker/toydb/tree/main/src/storage/testscripts/mvcc)
- [SQL execution tests](https://github.com/erikgrinaker/toydb/tree/main/src/sql/testscripts)
- [End-to-end tests](https://github.com/erikgrinaker/toydb/tree/main/tests/scripts)

Run tests with `cargo test`, or have a look at the latest
[CI run](https://github.com/erikgrinaker/toydb/actions/workflows/ci.yml).

## Benchmarks

toyDB is not optimized for performance, but comes with a `workload` benchmark tool that can run
various workloads against a toyDB cluster. For example:

```sh
# Start a 5-node toyDB cluster.
$ ./cluster/run.sh
[...]

# Run a read-only benchmark via all 5 nodes.
$ cargo run --release --bin workload read
Preparing initial dataset... done (0.179s)
Spawning 16 workers... done (0.006s)
Running workload read (rows=1000 size=64 batch=1)...

Time   Progress     Txns      Rate       p50       p90       p99      pMax
1.0s      13.1%    13085   13020/s     1.3ms     1.5ms     1.9ms     8.4ms
2.0s      27.2%    27183   13524/s     1.3ms     1.5ms     1.8ms     8.4ms
3.0s      41.3%    41301   13702/s     1.2ms     1.5ms     1.8ms     8.4ms
4.0s      55.3%    55340   13769/s     1.2ms     1.5ms     1.8ms     8.4ms
5.0s      70.0%    70015   13936/s     1.2ms     1.5ms     1.8ms     8.4ms
6.0s      84.7%    84663   14047/s     1.2ms     1.4ms     1.8ms     8.4ms
7.0s      99.6%    99571   14166/s     1.2ms     1.4ms     1.7ms     8.4ms
7.1s     100.0%   100000   14163/s     1.2ms     1.4ms     1.7ms     8.4ms

Verifying dataset... done (0.002s)
```

The available workloads are:

- `read`: single-row primary key lookups.
- `write`: single-row inserts to sequential primary keys.
- `bank`: bank transfers between various customers and accounts. To make things interesting, this
  includes joins, secondary indexes, sorting, and conflicts.

For more information about workloads and parameters, run `cargo run --bin workload -- --help`.

Example workload results are listed below. Write performance is atrocious, due to
[fsync](<https://en.wikipedia.org/wiki/Sync_(Unix)>) and a lack of write batching in the Raft layer.
Disabling fsync, or using the in-memory engine, significantly improves write performance (at the
expense of durability).

| Workload | BitCask     | BitCask w/o fsync | Memory      |
| -------- | ----------- | ----------------- | ----------- |
| `read`   | 14163 txn/s | 13941 txn/s       | 13949 txn/s |
| `write`  | 35 txn/s    | 4719 txn/s        | 7781 txn/s  |
| `bank`   | 21 txn/s    | 1120 txn/s        | 1346 txn/s  |

## Debugging

[VSCode](https://code.visualstudio.com) and the [CodeLLDB](https://marketplace.visualstudio.com/items?itemName=vadimcn.vscode-lldb)
extension can be used to debug toyDB, with the debug configuration under `.vscode/launch.json`.

Under the "Run and Debug" tab, select e.g. "Debug executable 'toydb'" or "Debug unit tests in
library 'toydb'".

## Smoke tests (all workload commands)

These commands run **small** benchmark configurations to verify the workloads work end-to-end.
They also produce CSV artifacts in `csv/` by default (see `--out-dir`).

> **Note:** Global flags must come **before** the subcommand:
> `--experiment`, `-n/--count`, `-c/--concurrency`, `-H/--hosts`, `--out-dir`, `-s/--seed`

### 1) Read smoke

```bash
cargo run --release --bin workload -- \
  --experiment smoke-read \
  -n 1000 -c 4 \
  read --rows 10000 --size 16 --batch 1
```

### 2) Write smoke

```bash
cargo run --release --bin workload -- \
  --experiment smoke-write \
  -n 500 -c 4 \
  write --size 16 --batch 10
```

### 3) Bank smoke

```bash
cargo run --release --bin workload -- \
  --experiment smoke-bank \
  -n 1000 -c 4 \
  bank --customers 50 --accounts 5 --balance 100 --max-transfer 10
```

### 4) Range Smoke

```bash
cargo run --release --bin workload -- \
  --experiment smoke-range \
  -n 1000 -c 4 \
  range --rows 10000 --size 16 --width 10
```

Optional: run them sequentially with `&&` to verify all workloads in one go:

```bash
set -e

cargo run --release --bin workload -- --experiment smoke-read  -n 1000 -c 4 read  --rows 10000 --size 16 --batch 1
cargo run --release --bin workload -- --experiment smoke-write -n 500  -c 4 write --size 16 --batch 10
cargo run --release --bin workload -- --experiment smoke-bank  -n 1000 -c 4 bank  --customers 50 --accounts 5 --balance 100 --max-transfer 10
cargo run --release --bin workload -- --experiment smoke-range -n 1000 -c 4 range --rows 10000 --size 16 --width 10
```

## Workload CLI reference

This section documents the `workload` benchmark CLI in full. The binary is defined in
`src/bin/workload.rs` and is built with `cargo build --release --bin workload`.

### Overview

The `workload` tool drives synthetic load against a running toyDB cluster and records throughput
and latency metrics. Its general invocation form is:

```
workload [GLOBAL FLAGS] <SUBCOMMAND> [SUBCOMMAND FLAGS]
```

> **Important:** all global flags must appear **before** the subcommand name.
> Flags placed after the subcommand name are interpreted as subcommand-specific flags and will
> cause a parse error if they are not recognised by that subcommand.

### Connecting to the cluster

By default, `workload` targets the 5-node local cluster started by `./cluster/run.sh`, which
listens on SQL ports `9601`–`9605`:

```
localhost:9601, localhost:9602, localhost:9603, localhost:9604, localhost:9605
```

You can override this with `-H` / `--hosts`, passing a comma-separated list of `host:port`
addresses. For example, to target only two nodes:

```bash
cargo run --release --bin workload -- -H localhost:9601,localhost:9602 read
```

### Workers and round-robin dispatch

When the benchmark starts, the runner spawns `--concurrency` worker threads. Workers are assigned
to hosts from the `--hosts` list in round-robin order: worker 0 connects to host 0, worker 1 to
host 1, and so on, wrapping around if there are more workers than hosts. Each worker then
independently issues requests in a tight loop until `--count` total transactions have been
completed across all workers. This spreads load evenly across every node in the cluster.

### Global flags

| Flag                  | Short | Default                             | Description                                                                                    |
| --------------------- | ----- | ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| `--hosts <LIST>`      | `-H`  | `localhost:9601,...,localhost:9605` | Comma-separated `host:port` list of toyDB SQL endpoints.                                       |
| `--concurrency <N>`   | `-c`  | `16`                                | Number of concurrent worker clients to spawn.                                                  |
| `--count <N>`         | `-n`  | `100000`                            | Total number of transactions to execute across all workers.                                    |
| `--seed <U64>`        | `-s`  | _(fixed default)_                   | RNG seed for the workload generator. Use a fixed seed for reproducible runs.                   |
| `--out-dir <PATH>`    |       | `csv`                               | Directory for CSV output files. Created automatically if it does not exist.                    |
| `--experiment <NAME>` |       | _(required)_                        | Human-readable experiment tag embedded in output filenames (e.g. `baseline`, `exp1-no-fsync`). |

### Subcommands

#### `read` — primary-key lookups

Executes single-row `SELECT` statements by primary key. Tests read throughput and latency under
a purely read workload.

| Flag             | Default | Description                              |
| ---------------- | ------- | ---------------------------------------- |
| `--rows <N>`     | `1000`  | Number of rows in the dataset.           |
| `--size <BYTES>` | `64`    | Size of each row's value field in bytes. |
| `--batch <N>`    | `1`     | Number of rows fetched per transaction.  |

Example:

```bash
cargo run --release --bin workload -- \
  --experiment my-read \
  -n 100000 -c 16 \
  read --rows 100000 --size 64 --batch 1
```

#### `write` — sequential inserts

Inserts rows with sequentially incrementing primary keys. Tests write throughput and measures the
cost of Raft consensus and fsync on the critical path.

| Flag             | Default | Description                              |
| ---------------- | ------- | ---------------------------------------- |
| `--size <BYTES>` | `64`    | Size of each row's value field in bytes. |
| `--batch <N>`    | `1`     | Number of rows inserted per transaction. |

Example:

```bash
cargo run --release --bin workload -- \
  --experiment my-write \
  -n 10000 -c 8 \
  write --size 64 --batch 1
```

#### `bank` — transactional transfers

Simulates a banking workload: transfers a random amount between randomly chosen accounts. Each
transaction reads account balances (with a join), checks constraints, and updates two rows. This
exercises MVCC conflict resolution, secondary indexes, and sorting.

| Flag                 | Default | Description                                 |
| -------------------- | ------- | ------------------------------------------- |
| `--customers <N>`    | `100`   | Number of customers in the dataset.         |
| `--accounts <N>`     | `10`    | Number of accounts per customer.            |
| `--balance <N>`      | `1000`  | Initial balance of each account.            |
| `--max-transfer <N>` | `100`   | Maximum amount transferred per transaction. |

Example:

```bash
cargo run --release --bin workload -- \
  --experiment my-bank \
  -n 50000 -c 16 \
  bank --customers 100 --accounts 10 --balance 1000 --max-transfer 100
```

#### `range` — range scans

Executes range-scan queries over contiguous key windows. Tests the query engine's ability to
stream rows and measures the overhead of returning multiple rows per transaction.

| Flag             | Default | Description                                         |
| ---------------- | ------- | --------------------------------------------------- |
| `--rows <N>`     | `1000`  | Total number of rows in the dataset.                |
| `--size <BYTES>` | `64`    | Size of each row's value field in bytes.            |
| `--width <N>`    | `10`    | Number of rows returned per range-scan transaction. |

Example:

```bash
cargo run --release --bin workload -- \
  --experiment my-range \
  -n 20000 -c 8 \
  range --rows 100000 --size 64 --width 50
```

### Output files

For every run, two CSV files are written to `--out-dir`:

**Per-second timeseries** — `<experiment>-<run_id>.csv`

One row is appended every second while the benchmark is running:

| Column     | Description                                        |
| ---------- | -------------------------------------------------- |
| `time_s`   | Elapsed time in seconds.                           |
| `progress` | Fraction of `--count` completed (0–1).             |
| `txns`     | Cumulative transactions completed so far.          |
| `rate_tps` | Transactions per second over the whole run so far. |
| `p50_ms`   | 50th-percentile latency in milliseconds.           |
| `p90_ms`   | 90th-percentile latency in milliseconds.           |
| `p99_ms`   | 99th-percentile latency in milliseconds.           |
| `max_ms`  | Maximum observed latency in milliseconds.          |

**Final summary** — `<experiment>-<run_id>-summary.csv`

A single row written after the run completes:

| Column         | Description                                                        |
| -------------- | ------------------------------------------------------------------ |
| `experiment`   | The `--experiment` tag.                                            |
| `run_id`       | Unix timestamp in milliseconds, used to uniquely identify the run. |
| `workload`     | Subcommand name (`read`, `write`, `bank`, `range`).                |
| `hosts`        | Semicolon-separated list of hosts used.                            |
| `concurrency`  | Value of `--concurrency`.                                          |
| `count`        | Value of `--count`.                                                |
| `seed`         | Value of `--seed`.                                                 |
| `total_time_s` | Wall-clock duration of the entire run in seconds.                  |
| `txns`         | Total transactions completed.                                      |
| `rate_tps`     | Overall throughput in transactions per second.                     |
| `p50_ms`       | Final 50th-percentile latency.                                     |
| `p90_ms`       | Final 90th-percentile latency.                                     |
| `p99_ms`       | Final 99th-percentile latency.                                     |
| `max_ms`      | Final maximum latency.                                             |

The `run_id` suffix on both filenames ensures that repeated runs with the same `--experiment` tag
do not overwrite each other.

## Credits

The toyDB logo is courtesy of [@jonasmerlin](https://github.com/jonasmerlin).
