# <a><img src="./docs/architecture/images/toydb.svg" height="40" valign="top" /></a> toyDB

## Prerequisite
- Rust
- Python
- GCP CLI

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
$ cargo run --release --bin workload -- --experiment sample-exp --cache read
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

### BlockGen flow — how work items are generated

The `read` workload generates work items with `BlockGen` (`src/bin/workload.rs`), an
iterator that alternates between **fresh** key blocks (never used before, always a cache
miss) and **reused** key blocks (sampled from already-seen keys) in fixed-size blocks
(`--block-size`, default `100`; each batch is `--batch`, default `1` key):

```
BlockGen::next() — one call returns one work item (a batch of key ids)
========================================================================
        |
        v
  +-------------------------------------------------------------+
  | (1) end of current block?  (block_remaining == 0)           |
  |       yes -> flip is_fresh_block (fresh <-> reused)         |
  |              block_remaining = block_size                   |
  |       no  -> keep the current block type                    |
  +-------------------------------------------------------------+
        |
        v
  +-------------------------------------------------------------+
  | (2) n = min(batch, block_remaining); block_remaining -= n  |
  +-------------------------------------------------------------+
              |                               |
              |  fresh block                  |  reused block
              v                               v
  +------------------------+      +---------------------------+
  | (3a) FRESH block       |      | (3b) REUSED block         |
  | for each of n ids:     |      | for each of n ids:        |
  |   if fresh_keys left:  |      |   sample uniformly or     |
  |     take fresh_keys[   |      |   zipf(skew) from         |
  |     fresh_idx],        |      |   used_keys               |
  |     fresh_idx += 1,    |      |                           |
  |     push id to         |      |                           |
  |     used_keys          |      |                           |
  |   else: sample from    |      |                           |
  |     used_keys          |      |                           |
  +------------------------+      +---------------------------+
              |                               |
              +---------------+---------------+
                              |
                              v
                return work item (HashSet of n ids)
                              |
                              v
  +-------------------------------------------------------------+
  | runner loop: stop flag set? (30s deadline elapsed)          |
  |       yes -> break -> benchmark ends                        |
  |       no  -> send batch to workers, call next() again       |
  +-------------------------------------------------------------+
```

Notes:

- `fresh_keys` is built once in `generate()` as `shuffle(1..=rows)`, so fresh ids are
  handed out in random order and never repeated until the list is exhausted.
- When `fresh_keys` runs out (every row id has been used once), fresh blocks fall back to
  sampling from `used_keys`, exactly like reused blocks.
- The benchmark is **time-bounded**: the generator thread loops over `BlockGen` until a
  `stop` flag is set by the 30s deadline; it is not bounded by a request count.
- A work item is a `HashSet<u64>`, so a batch never contains duplicate ids.

## Terraform Workflow

A 5-node toyDB cluster can be deployed on GCP via Terraform.

### 1. Deploy

```bash
cd terraform
terraform init
terraform apply
```

This creates:
- A VPC network + subnet
- 5 VM instances (Ubuntu 22.04, `e2-medium` by default)
- Firewall rules: SSH (anywhere), SQL ports (configurable via `client_cidrs`), Raft (internal only)
- A startup script installs Rust + builds toyDB and registers `toydb` as a systemd service on each node

Key variables (`terraform/variables.tf`):

| Variable | Default | Description |
|----------|---------|-------------|
| `project_id` | `cogent-dragon-451411-m4` | GCP project ID |
| `region` | `europe-west3` | GCP region |
| `zone` | `europe-west3-c` | GCP zone |
| `prefix` | `toydb` | Resource name prefix |
| `machine_type` | `e2-medium` | VM machine type |
| `disk_size_gb` | `20` | Boot disk size |
| `client_cidrs` | `["0.0.0.0/0"]` | CIDRs allowed to connect to SQL ports |

### 2. Validate and get host addresses

Wait for all 5 nodes to finish startup and register the `toydb` service:

```bash
bash terraform/validate-VMs.sh [zone] [prefix]
```

Once ready, retrieve the external IPs with SQL ports:

```bash
bash terraform/get-hosts.sh [zone] [prefix]
```

Example output:

```
  toydb-node-1: 35.198.XX.XX
  toydb-node-2: 34.159.XX.XX
  ...

  export TOYDB_HOSTS="35.198.XX.XX:9601,34.159.XX.XX:9602,..."
```

### 3. Set environment variable

```bash
export TOYDB_HOSTS="35.198.XX.XX:9601,34.159.XX.XX:9602,35.198.XX.XX:9603,34.159.XX.XX:9604,35.198.XX.XX:9605"
```

All experiment scripts in `scripts/cloud/` read `$TOYDB_HOSTS` automatically via `HOST_FLAG="-H $TOYDB_HOSTS"`.

### 4. Run experiments

Experiment scripts are organized by experiment number under `scripts/cloud/`:

| Directory | Experiment |
|-----------|------------|
| `exp1/` | Cache vs no-cache |
| `exp2/` | FIFO vs LRU eviction |
| `exp3/` | Concurrency scaling (M/M/m model) |
| `exp3-no-cache/` | No-cache baseline for concurrency scaling |

```bash
# Single experiment (e.g. exp1, cache, large, zipf, run ID 1)
bash scripts/cloud/exp1/cache/l/zipf.sh 1

# Full experiment (all 5 runs)
for id in 1 2 3 4 5; do bash scripts/cloud/exp1/cache/l/zipf.sh "$id"; done

# Or use the runner for exp1
bash scripts/cloud/exp1/run-all.sh
```

### 5. Generate charts

See [`plot/README.md`](plot/README.md) for detailed usage of all plotting scripts.

### 6. Tear down

```bash
cd terraform
terraform destroy
```

### Sanitize

To wipe cluster data and restart the nodes (without re-deploying):

```bash
bash scripts/sanitize-cloud.sh
```


## Debugging

[VSCode](https://code.visualstudio.com) and the [CodeLLDB](https://marketplace.visualstudio.com/items?itemName=vadimcn.vscode-lldb)
extension can be used to debug toyDB, with the debug configuration under `.vscode/launch.json`.

Under the "Run and Debug" tab, select e.g. "Debug executable 'toydb'" or "Debug unit tests in
library 'toydb'".

## Credits

The toyDB logo is courtesy of [@jonasmerlin](https://github.com/jonasmerlin).
