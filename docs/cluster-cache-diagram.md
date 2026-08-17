# Cluster and Cache Structure (GCP deployment)

## 1. Structure

The numbers `(1)`-`(6)` trace the benchmark dataflow - see section 2 for the
detailed flow.

```
                  Benchmark loader (workload binary)
                    +----------------------------------------------------------------+
                    | Worker 1   Worker 2   ...   Worker N                           |
                    | (one TCP connection each, closed-loop)                         |
                    | (1) Worker generates a batch of key IDs (HashSet<u64>)         |
                    |                                                                |
                    |  +----------------------------------------------------------+  |
                    |  | (2) filter_uncached(): HIT -> skip SQL | MISS -> (3)     |  |
                    |  | Client-side cache (shared, one global Mutex)             |  |
                    |  | LRU / FIFO eviction, default max size 5,000              |  |
                    |  +----------------------------------------------------------+  |
                    +-------------------------------+--------------------------------+
                                                    |
                                                    |  (3) MISS -> SELECT id, value FROM "read" ...
                                                    |  (Phase 1) via EXTERNAL IPs 34.x.x.x:9601-9605  - from your machine, over public internet
                                                    |  (Phase 2) via INTERNAL IPs 10.0.0.x:9601-9605  - loader runs on node-1, inside the VPC
                                                    |  firewall toydb-allow-sql: TCP 9601-9605 open to client_cidrs (default 0.0.0.0/0)
                                                    v
  +----------------------------------------------------------------------------------------------------+
  |GCP VPC toydb-vpc / subnet 10.0.0.0/24  (region europe-west3, zone europe-west3-c)                  |
  |(4) receiving node: SQL server -> forwards to Raft leader -> leader executes read                   |
  |each VM: listens on 0.0.0.0:960N/970N, peers = other nodes' INTERNAL IPs                            |
  |                                                                                                    |
  |+----------------+  +----------------+  +----------------+  +----------------+  +----------------+  |
  |   toydb-node-1        toydb-node-2        toydb-node-3        toydb-node-4        toydb-node-5     |
  |   int 10.0.0.2        int 10.0.0.3        int 10.0.0.4        int 10.0.0.5        int 10.0.0.6     |
  |   ext 34.x.x.x        ext 34.x.x.x        ext 34.x.x.x        ext 34.x.x.x        ext 34.x.x.x     |
  |    SQL :9601           SQL :9602           SQL :9603           SQL :9604           SQL :9605       |
  |    Raft :9701          Raft :9702          Raft :9703          Raft :9704          Raft :9705      |
  |+----------------+  +----------------+  +----------------+  +----------------+  +----------------+  |
  |        |                   |                   |                   |                   |           |
  |        +-------------------+-------------------+-------------------+-------------------+           |
  |(6) leader replicates writes to all 5 nodes (commit needs a quorum of 3)                            |
  |Raft :9701-9705 INTERNAL only (firewall toydb-allow-raft: TCP 9701-9705 from 10.0.0.0/24)           |
  +----------------------------------------------------------------------------------------------------+
```

## 2. Benchmark flow (one work item)

```
Benchmark flow - one work item (read workload)
================================================================

 (1) Worker generates a batch of key IDs (HashSet<u64>)
        |
        v
 (2) cache::filter_uncached(batch)     <-- locks the shared cache
        |
        +-- HIT: key already cached
        |        -> no SQL query (LRU: move to MRU end / FIFO: no-op)
        |
        +-- MISS: key not in cache
        |
        v
 (3) SELECT id, value FROM "read" WHERE id = ...
        |     one TCP connection per worker; nodes chosen round-robin
        v
 (4) Receiving node (any of the 5 VMs):
        |     - SQL server receives the query
        |     - if this node is a follower, it forwards the request
        |       to the Raft leader (internal network, ports 9701-9705)
        |     - leader confirms it is still the leader (quorum round-trip)
        |     - leader executes the read on its local storage engine
        v
 (5) Rows returned to the worker -> cache::insert(id, value)
        |     (evicts the LRU/FIFO tail entry if cache is over max size)
        v
 (6) Worker records latency (HDR histogram)
        |     -> next work item -> back to (1)
        v
      repeat until --count / --duration is reached
      every second: throughput + p50/p90/p99/max + cache hit rate -> CSV
```

Reads are only executed on the **leader** (for linearizability); they are
never appended to the Raft log. A read on a follower is forwarded to the
leader, and the result is forwarded back.

## 3. Write dataflow (dataset preparation)

Before the timed run, the loader creates the table and inserts the dataset in
a single transaction (`prepare()` in `src/bin/workload.rs`):

```
 CREATE TABLE "read" + INSERT ... COMMIT
        |   (rows inserted in chunks of 100, one transaction)
        v
 write request -> Raft leader (any node forwards it if needed)
        |
        v
 leader appends to its log and replicates to all 4 followers
        |
        v
 commit once a quorum (3 of 5 nodes) acknowledges the entry
        |
        v
 every node applies the write to its own storage engine
   -> each of the 5 VMs keeps a full copy of the dataset
```

## Logical port -> physical port mapping

Same formula everywhere (local cluster and GCP VMs): node ID `N` -> SQL
`9600 + N`, Raft `9700 + N`. On the VMs the startup script writes
`listen_sql: 0.0.0.0:960N` / `listen_raft: 0.0.0.0:970N` and sets `peers` to
the other nodes' **internal** IPs.

| Logical (service)        | Node 1         | Node 2         | Node 3         | Node 4         | Node 5         |
| ------------------------ | -------------- | -------------- | -------------- | -------------- | -------------- |
| SQL (clients / workload) | `:9601`        | `:9602`        | `:9603`        | `:9604`        | `:9605`        |
| Raft (node-to-node)      | `:9701`        | `:9702`        | `:9703`        | `:9704`        | `:9705`        |
| VM                       | `toydb-node-1` | `toydb-node-2` | `toydb-node-3` | `toydb-node-4` | `toydb-node-5` |

Example addresses from a real deployment (`cluster/README.md`, output of
`terraform apply`):

| VM             | Internal IP | External IP      | SQL              | Raft             |
| -------------- | ----------- | ---------------- | ---------------- | ---------------- |
| `toydb-node-1` | `10.0.0.9`  | `34.107.42.7`    | `10.0.0.9:9601`  | `10.0.0.9:9701`  |
| `toydb-node-2` | `10.0.0.10` | `34.141.67.247`  | `10.0.0.10:9602` | `10.0.0.10:9702` |
| `toydb-node-3` | `10.0.0.7`  | `34.89.135.54`   | `10.0.0.7:9603`  | `10.0.0.7:9703`  |
| `toydb-node-4` | `10.0.0.11` | `34.159.236.102` | `10.0.0.11:9604` | `10.0.0.11:9704` |
| `toydb-node-5` | `10.0.0.8`  | `35.246.179.56`  | `10.0.0.8:9605`  | `10.0.0.8:9705`  |

(IPs change every time you `terraform apply` - use `get-hosts.sh` /
`get-internal-hosts.sh` to fetch the current ones.)

## Firewall rules (`terraform/main.tf`)

| Rule               | Ports         | Allowed from                         | Purpose                       |
| ------------------ | ------------- | ------------------------------------ | ----------------------------- |
| `toydb-allow-ssh`  | TCP 22        | `0.0.0.0/0`                          | SSH provisioning              |
| `toydb-allow-sql`  | TCP 9601-9605 | `client_cidrs` (default `0.0.0.0/0`) | SQL clients / workload loader |
| `toydb-allow-raft` | TCP 9701-9705 | `10.0.0.0/24` only                   | Raft between the 5 nodes      |

## How the loader connects

- The workload loader only ever talks to the **SQL ports** (`9601`-`9605`),
  via the `$TOYDB_HOSTS` environment variable
  (e.g. `export TOYDB_HOSTS="10.0.0.9:9601,10.0.0.10:9602,..."`).
- **Phase 1** - loader runs on your local machine and connects to the VMs
  through their **external** IPs (`34.x.x.x`), crossing the public internet
  and the SQL firewall. Each transaction pays tens of ms of RTT.
- **Phase 2** - loader runs on `toydb-node-1` inside the VPC and connects to
  the **internal** IPs (`10.0.0.x`), staying inside the datacenter with
  sub-ms latency. This is why Phase 2 throughput is ~2.3-4.8x higher.
- Raft traffic (`9701`-`9705`) is **internal-only**: nodes discover each
  other via the `peers` list written to `toydb.yaml` by the startup script,
  which always uses internal IPs. External clients can never reach the Raft
  ports.
