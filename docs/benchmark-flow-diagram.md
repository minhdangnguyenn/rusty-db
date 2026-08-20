# Benchmark Flow: Local vs Cloud Deployment

## 1. Overview — Where does the benchmark run?

There are **two deployment modes**, depending on which experiment phase you are running:

|                                | Phase 1 (local loader)   | Phase 2 (cloud loader)                |
| ------------------------------ | ------------------------ | ------------------------------------- |
| **Loader runs on**             | Your local machine       | `toydb-node-1` inside GCP             |
| **Connects to nodes via**      | External IPs `34.x.x.x`  | Internal IPs `10.0.0.x`               |
| **Network path**               | Public internet → VPC    | Inside VPC only                       |
| **Latency per SQL round-trip** | ~10-50 ms (internet RTT) | < 1 ms (same datacenter)              |
| **Typical throughput**         | Lower                    | 2-5× higher                           |
| **Used in**                    | Phase 1 experiments      | Phase 2 experiments (exp3, modelling) |

---

## 2. Phase 1 — Loader on your local machine

```
  YOUR LOCAL MACHINE
  ┌─────────────────────────────────────────────────────────┐
  │  cargo run --release --bin workload --                  │
  │    -H 34.107.42.7:9601,34.141.67.247:9602,...          │
  │    -c 4 read --rows 1000 --cache --dist zipf           │
  │                                                         │
  │  ┌───────────────┐                                      │
  │  │  Loader        │                                     │
  │  │  K workers     │                                     │
  │  │  + cache       │                                     │
  │  └───────┬───────┘                                      │
  └──────────┼──────────────────────────────────────────────┘
             │
             │  SQL queries over PUBLIC INTERNET
             │  (external IPs 34.x.x.x:9601-9605)
             │  firewall: toydb-allow-sql (TCP 9601-9605)
             │  latency: ~10-50 ms per round-trip
             │
             v
  ┌──────────────────────────────────────────────────────────────────────┐
  │  GCP VPC toydb-vpc / subnet 10.0.0.0/24                            │
  │                                                                      │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│
  │  │ node-1   │  │ node-2   │  │ node-3   │  │ node-4   │  │ node-5 ││
  │  │SQL:9601  │  │SQL:9602  │  │SQL:9603  │  │SQL:9604  │  │SQL:9605││
  │  │Raft:9701 │  │Raft:9702 │  │Raft:9703 │  │Raft:9704 │  │Raft:9705│
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘│
  │       └────────────── Raft replication (internal) ──────────────┘   │
  └──────────────────────────────────────────────────────────────────────┘
```

**What happens:** The loader on your laptop opens TCP connections to the 5 external IPs. Each SQL query crosses the public internet, enters the VPC through the SQL firewall, hits a node, and the response travels back. The internet RTT dominates the latency.

---

## 3. Phase 2 — Loader on `toydb-node-1` (inside the VPC)

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  GCP VPC toydb-vpc / subnet 10.0.0.0/24                              │
  │                                                                      │
  │  ┌──────────────────────────────┐                                    │
  │  │  toydb-node-1 (10.0.0.9)     │                                    │
  │  │                              │                                    │
  │  │  ┌────────────────────────┐  │                                    │
  │  │  │  Loader (benchmark)    │  │                                    │
  │  │  │  cargo run --release   │  │                                    │
  │  │  │  --bin workload        │  │                                    │
  │  │  │  -H 10.0.0.9:9601,     │  │                                    │
  │  │  │      10.0.0.10:9602,   │  │                                    │
  │  │  │      10.0.0.7:9603,    │  │  SQL queries over INTERNAL         │
  │  │  │      10.0.0.11:9604,   │──┼────── network (sub-ms RTT) ──┐     │
  │  │  │      10.0.0.8:9605     │  │                              │     │
  │  │  │  -c 4 read --rows 1000 │  │                              │     │
  │  │  │  --cache --dist zipf   │  │                              │     │
  │  │  └────────────────────────┘  │                              │     │
  │  └──────────────────────────────┘                              │     │
  │                                                                │     │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │     │
  │  │ node-2   │  │ node-3   │  │ node-4   │  │ node-5   │        │     │
  │  │SQL:9602  │  │SQL:9603  │  │SQL:9604  │  │SQL:9605  │        │     │
  │  │Raft:9702 │  │Raft:9703 │  │Raft:9704 │  │Raft:9705 │        │     │
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │     │
  │       └────────────── Raft replication (internal) ─────────────┘     │
  └──────────────────────────────────────────────────────────────────────┘
```

**What happens:** The loader runs directly on `toydb-node-1` alongside the database process. It connects to all 5 nodes (including itself) via internal IPs. No public internet involved — everything stays inside the VPC. This is why Phase 2 throughput is 2-5× higher.

---

## 4. Workload flow (both phases)

This is the lifecycle of **one work item** inside the loader, identical for both phases:

```
  Worker (one of K concurrent workers)
  ═══════════════════════════════════════════════════════════════

  (1) BlockGen produces a batch of key IDs (HashSet<u64>)
        │
        v
  (2) filter_uncached(batch)  ──── locks shared cache (Mutex)
        │
        ├── HIT:  key already in cache
        │         -> skip SQL, move to MRU (LRU) or no-op (FIFO)
        │         -> go to (5)
        │
        └── MISS: key NOT in cache
              │
              v
  (3) SELECT id, value FROM "read" WHERE id = ?
        │     sent over TCP to one of the 5 SQL ports (round-robin)
        │
        │     ┌──────────────────────────────────────────────┐
        │     │  PHASE 1: goes over public internet          │
        │     │  PHASE 2: stays inside VPC (< 1 ms)          │
        │     └──────────────────────────────────────────────┘
        │
        v
  (4) Receiving node executes the query
        │     - if follower: forward to Raft leader (internal)
        │     - leader confirms leadership (quorum round-trip)
        │     - leader executes read on local storage
        │     - rows returned to worker
        │
        v
  (5) cache::insert(id, value)  ──── fills the client-side cache
        │     evicts LRU/FIFO tail if over max_size (5000)
        │
        v
  (6) Record latency (HDR histogram)
        │
        v
  (7) Loop back to (1) with next batch
        │
        └── repeat until --duration (30s) expires
```

### BlockGen alternation (controls cache hit rate)

```
  BlockGen state machine (src/bin/workload.rs)
  ═══════════════════════════════════════════════

  fresh_keys = [1..rows] shuffled
  used_keys  = []

  ┌──────────────┐     block_size IDs     ┌──────────────┐
  │  FRESH block  │ ───────────────────▶  │ REUSED block │
  │               │                       │              │
  │ Take IDs from │  every block_size     │ Sample from  │
  │ fresh_keys    │  (default 100),       │ used_keys    │
  │ (never used)  │  flip state           │ (already seen)│
  │               │                       │              │
  │ → cache MISS  │                       │ → cache HIT  │
  │ → fills cache │                       │ → fast path  │
  └──────────────┘                        └──────────────┘
        ▲                                        │
        └────────────────────────────────────────┘
                    flip every block_size IDs

  When fresh_keys is exhausted (all IDs used at least once),
  FRESH blocks also sample from used_keys.
```

---

## 5. Scripts: how to run each phase

### Phase 1 — local loader

```bash
# Set the external IPs (from terraform output or get-hosts.sh)
export TOYDB_HOSTS="34.107.42.7:9601,34.141.67.247:9602,34.89.135.54:9603,34.159.236.102:9604,35.246.179.56:9605"

# Run from your local machine
cargo run --release --bin workload -- \
  -H $TOYDB_HOSTS \
  -c 4 --id 1 read --rows 1000 --cache --dist zipf
```

### Phase 2 — cloud loader (on node-1)

```bash
# SSH into toydb-node-1
gcloud compute ssh toydb-node-1 --zone europe-west3-c

# Set internal IPs (from get-internal-hosts.sh)
export TOYDB_HOSTS="10.0.0.9:9601,10.0.0.10:9602,10.0.0.7:9603,10.0.0.11:9604,10.0.0.8:9605"

# Run from inside the VPC
cargo run --release --bin workload -- \
  -H $TOYDB_HOSTS \
  -c 4 --id 1 read --rows 1000 --cache --dist zipf
```

---

## 6. Phase 1 vs Phase 2 — why the difference matters

```
  Phase 1 (local)                    Phase 2 (cloud)
  ══════════════                     ══════════════

  Loader ──── internet ──── VPC      Loader (on node-1)
    │                                     │
    │  ~10-50 ms RTT                      │  < 1 ms RTT
    │  per SQL query                      │  per SQL query
    │                                     │
    v                                     v
  Node (SQL:960N)                    Node (SQL:960N)
    │                                     │
    │  Raft (internal)                    │  Raft (internal)
    v                                     v
  Follower ←── Leader              Follower ←── Leader

  Throughput: ~1-3K ops/s           Throughput: ~5-15K ops/s
  (internet latency dominates)      (sub-ms, server-bound)
```

The key insight: **the database code is identical in both phases** — only the network path changes. Phase 2 removes the internet bottleneck, revealing the true server-side performance and queueing behavior that the M/M/m model captures.
