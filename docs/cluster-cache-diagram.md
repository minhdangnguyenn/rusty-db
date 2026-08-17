# Cluster and Cache Structure (GCP deployment)

## Diagram

```
                  Benchmark loader (workload binary)                                  
                    +----------------------------------------------------------------+
                    | Worker 1   Worker 2   ...   Worker N                           |
                    | (one TCP connection each, closed-loop)                         |
                    |                                                                |
                    |  +----------------------------------------------------------+  |
                    |  | Client-side cache (shared, one global Mutex)             |  |
                    |  | LRU / FIFO eviction, default max size 5,000              |  |
                    |  +----------------------------------------------------------+  |
                    +-------------------------------+--------------------------------+
                                                    |
                                                    |  cache miss -> SELECT id, value FROM "read" ...
                                                    |  (Phase 1) via EXTERNAL IPs 34.x.x.x:9601-9605  - from your machine, over public internet
                                                    |  (Phase 2) via INTERNAL IPs 10.0.0.x:9601-9605  - loader runs on node-1, inside the VPC
                                                    |  firewall toydb-allow-sql: TCP 9601-9605 open to client_cidrs (default 0.0.0.0/0)
                                                    v
  +----------------------------------------------------------------------------------------------------+
  |GCP VPC toydb-vpc / subnet 10.0.0.0/24  (region europe-west3, zone europe-west3-c)                  |
  |each VM runs one toydb node: listens on 0.0.0.0, peers = other nodes' INTERNAL IPs                  |
  |                                                                                                    |
  |+----------------+  +----------------+  +----------------+  +----------------+  +----------------+  |
  |   toydb-node-1        toydb-node-2        toydb-node-3        toydb-node-4        toydb-node-5     |
  |   int 10.0.0.x        int 10.0.0.x        int 10.0.0.x        int 10.0.0.x        int 10.0.0.x     |
  |   ext 34.x.x.x        ext 34.x.x.x        ext 34.x.x.x        ext 34.x.x.x        ext 34.x.x.x     |
  |    SQL :9601           SQL :9602           SQL :9603           SQL :9604           SQL :9605       |
  |    Raft :9701          Raft :9702          Raft :9703          Raft :9704          Raft :9705      |
  |+----------------+  +----------------+  +----------------+  +----------------+  +----------------+  |
  |        |                   |                   |                   |                   |           |
  |        +-------------------+-------------------+-------------------+-------------------+           |
  |Raft :9701-9705 - INTERNAL only (firewall toydb-allow-raft: TCP 9701-9705 from 10.0.0.0/24)         |
  +----------------------------------------------------------------------------------------------------+
```

## Logical port -> physical port mapping

Same formula everywhere (local cluster and GCP VMs): node ID `N` -> SQL
`9600 + N`, Raft `9700 + N`. On the VMs the startup script writes
`listen_sql: 0.0.0.0:960N` / `listen_raft: 0.0.0.0:970N` and sets `peers` to
the other nodes' **internal** IPs.

| Logical (service) | Node 1 | Node 2 | Node 3 | Node 4 | Node 5 |
|---|---|---|---|---|---|
| SQL (clients / workload) | `:9601` | `:9602` | `:9603` | `:9604` | `:9605` |
| Raft (node-to-node) | `:9701` | `:9702` | `:9703` | `:9704` | `:9705` |
| VM | `toydb-node-1` | `toydb-node-2` | `toydb-node-3` | `toydb-node-4` | `toydb-node-5` |
| Config | `terraform/main.tf` + startup script (generates `toydb.yaml` on each VM) | | | | |

Example addresses from a real deployment (`cluster/README.md`, output of
`terraform apply`):

| VM | Internal IP | External IP | SQL | Raft |
|---|---|---|---|---|
| `toydb-node-1` | `10.0.0.9` | `34.107.42.7` | `10.0.0.9:9601` | `10.0.0.9:9701` |
| `toydb-node-2` | `10.0.0.10` | `34.141.67.247` | `10.0.0.10:9602` | `10.0.0.10:9702` |
| `toydb-node-3` | `10.0.0.7` | `34.89.135.54` | `10.0.0.7:9603` | `10.0.0.7:9703` |
| `toydb-node-4` | `10.0.0.11` | `34.159.236.102` | `10.0.0.11:9604` | `10.0.0.11:9704` |
| `toydb-node-5` | `10.0.0.8` | `35.246.179.56` | `10.0.0.8:9605` | `10.0.0.8:9705` |

(IPs change every time you `terraform apply` - use `get-hosts.sh` /
`get-internal-hosts.sh` to fetch the current ones.)

## Firewall rules (`terraform/main.tf`)

| Rule | Ports | Allowed from | Purpose |
|---|---|---|---|
| `toydb-allow-ssh` | TCP 22 | `0.0.0.0/0` | SSH provisioning |
| `toydb-allow-sql` | TCP 9601-9605 | `client_cidrs` (default `0.0.0.0/0`) | SQL clients / workload loader |
| `toydb-allow-raft` | TCP 9701-9705 | `10.0.0.0/24` only | Raft between the 5 nodes |

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
