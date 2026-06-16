# <a><img src="./docs/architecture/images/toydb.svg" height="40" valign="top" /></a> toyDB

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

## Benchmarks

toyDB is not optimized for performance, but comes with a `workload` benchmark tool that can run
various workloads against a toyDB cluster. For example:

```sh
# Start a 5-node toyDB cluster.
$ ./cluster/run.sh
[...]

# Run a read-only benchmark via all 5 nodes.
$ cargo run --release --bin workload -- --expriment sample read
Preparing initial dataset... done (0.179s)
Spawning 16 workers... done (0.006s)
Running workload read (rows=1000 size=64 batch=1)...

Time   Progress     Txns      Rate       p50       p90       p99       max
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

## My scripts

### Run experiments

```bash
bash scripts/<cache or no-cache>/<experiment-name>.sh <experiment-id>
```

e.g.,

```bash
bash scripts/no-cache/no-cache-read-s-uniform.sh 1
```

The id defaults to `1` if omitted.

### Plot charts

Requires `python3` with `matplotlib` and `numpy`. Virtualenv: `plot/.venv/`.

```bash
# Single experiment (timeseries)
bash plot/plot.sh csv/no-cache-read-s-uniform-1.csv
# -> charts/<name>-throughput.png, charts/<name>-latency.png

# Compare throughput (two experiments, overlay)
bash plot/plot-compare-throughput.sh csv/no-cache.csv csv/cache.csv
# -> charts/compare-throughput-*.png

# Compare latency (two experiments, grouped bar + difference)
bash plot/plot-compare-latency.sh csv/no-cache-summary.csv csv/cache-summary.csv
# -> charts/comparison-latency.png

# Compare both
bash plot/plot-compare.sh csv/no-cache.csv csv/cache.csv
# -> both compare charts
```

### Sanitize

Use the sanitize script to wipe cluster data and restart the nodes if needed:

```bash
bash scripts/sanitize.sh
```

### Cache throughput explanation

when cache is enabled, throughput is high from the start, not gradually climbing.
the first ~10,000 transactions are cache misses (10,000 unique rows). each miss
queries the db, but the db response is still fast (~1.5ms p50). the cache stores
the result.

the remaining ~90,000 transactions are cache hits — the ids are already in the
hashmap. no db call. just a local lock + hash lookup (microseconds).

throughput stays near-maximum from second 1 because the cache miss phase (first
10k reads) completes within the first second. after that, every read is instant
— no network, no raft, no disk. the system is cpu-bound on hash lookups, not
i/o-bound on database queries.

### Throughput scaling with concurrency

experiments with 1, 4, 8, and 16 workers show that throughput scales
near-linearly at ~2,000 tps per worker. all runs are flat from start to finish
— no throughput dip in the first 2 seconds. the earlier observed variation was
just normal measurement noise, not a systematic pattern.

# Available Workloads (default)

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

## Credits

The toyDB logo is courtesy of [@jonasmerlin](https://github.com/jonasmerlin).
