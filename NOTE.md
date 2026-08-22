Confirmed from your own data. Here's the phase‑1 vs phase‑2 comparison for identical `exp1` runs (both `concurrency=16`, `count=100000`, `duration=30`, `rows=10000`, same seed):

| Run | Phase 1 (`csv/cloud`) | Phase 2 (`csv/p2`) | Speedup |
|---|---|---|---|
| `no-cache` uniform | 831 /s | 2,907 /s | **~3.5×** |
| `no-cache` zipf | 1,703 /s | 4,063 /s | **~2.4×** |
| `cache` uniform | 2,590 /s | 6,045 /s | **~2.3×** |
| `cache` zipf | 8,116 /s | 39,196 /s | **~4.8×** |

The giveaway is in the **`hosts` column** of each CSV:

- **Phase 1 (`csv/cloud`)** record:
  ```
  hosts = "34.185.187.3:9601;34.185.213.229:9602;34.40.113.67:9603;..."
  ```
- **Phase 2 (`csv/p2`)** record:
  ```
  hosts = "10.0.0.2:9601;10.0.0.3:9602;10.0.0.5:9603;10.0.0.6:9604;10.0.0.4:9605"
  ```

So the real cause is **where the benchmark loader ran and which network path it used**, not the DB itself changing:

## Primary reason: network path / loader location

- **Phase 1** — you ran the `workload` binary from your **local dev machine**, connecting to the VMs through their **external/public IPs (`34.x.x.x`)**. Every SQL request went: local → public internet → GCP gateway/firewall → VM → raft round-trip, and back → public internet. That adds **tens of ms of RTT + jitter** per transaction.
- **Phase 2** — in the "run benchmark on VM" commit you moved the loader **onto node‑1**, inside the same VPC, and connected via the **internal `10.0.0.x` IPs** (`get-internal-hosts.sh`). Requests now stay inside the datacenter with sub‑ms latency and almost no jitter.

That's exactly what the latencies show:

| Run | Phase 1 p50 (ms) | Phase 2 p50 (ms) |
|---|---|---|
| `no-cache` uniform | 16.9 | 5.8 |
| `no-cache` zipf | 7.1 | 3.9 |

Roughly half the per‑request latency → ~2.4–3.5× throughput on the network-bound (`no-cache`) cases.

## Why the `cache` zipf case is even more dramatic (4.8×)

At ~89–99% cache hit rate, most requests are served **from the client-side cache in the OS** (p50 ≈ 0.0005 ms), so the network barely matters for them. But the ~11% of misses are latency-bound, and in phase 1 those misses each paid the public-internet round-trip. With internal-IP misses at ~1 ms instead of ~20 ms, the whole pipeline drains far faster and the cache-hit path can run at its true ceiling:

- `cache-l-zipf`: Phase 1 **8,116** → Phase 2 **39,196**
- `cache-s-zipf` (rows=1000, 99.99% hit): Phase 1 **1,308,225** → Phase 2 **1,978,555** — only ~1.5×, because here almost every request is a pure-cache hit that never touches the network; the small remaining gap is the miss path + jitter.

This is actually a good sanity proof: the bigger the network share of each transaction, the bigger the phase‑1→p2 gap.

## Secondary contributing factors (minor, not the root cause)

- **Stability fixes** from the same VM commit (`RAFT_PEER_CHANNEL_CAPACITY 50_000`, `--timeout`, stop-all/wipe/start-all `sanitize-cloud.sh`) reduced mid-run stalls/panics, so p2 runs sustain throughput instead of dipping. This makes the *quality* of the number better, but the level difference vs `csv/cloud` is overwhelmingly network/loader‑location.
- Same config otherwise (concurrency, count, rows, seed all identical), so it's not a concurrency parameter change.

**Bottom line:** the jump comes from removing the public-internet hop by (a) running the loader inside the VPC and (b) talking to the `10.0.0.x` internal IPs. The CSVs' own `hosts` columns (`34.x.x.x` → `10.0.0.x`) are the smoking gun. For a fair cross-phase comparison in your report you'd want to note that **phase1 = remote loader over public IPs, phase2 = dedicated loader inside the VMs' network**, because the DB throughput itself didn't change between phases — the client path did.

-------------------------------------------------------------------------------------------
# WHY THROUGHPUT GROWTHS NOT LINEARLY IN SMALL DATASET (NOT LIKE BIG DATASET) ? (AI ANSWER)
Good call to re-check — I need to correct one thing from my earlier answers first, then explain with the actual numbers.

Correction on units

My earlier "throughput" figures for the cache cases were actually the  txns  column (total over the ~30 s run), not per-second throughput. The shapes of the curves were right, but the absolute values were ~30× too high. The correct per-second numbers (CSV column  throughput , run 1) are:

Small dataset, cache (rows=1000, uniform) — hit rate ≈ 99.998%:

```text
┌─────┬──────────────┐
│ c   │ throughput   │
├─────┼──────────────┤
│ c4  │ 1,761,341 /s │
│ c8  │ 1,727,893 /s │
│ c16 │ 1,654,749 /s │
│ c32 │ 1,127,480 /s │
│ c64 │ 1,438,652 /s │
└─────┴──────────────┘
```

Large dataset, cache (rows=10000, uniform) — hit rate ≈ 49–50%:

```text
┌─────┬────────────┐
│ c   │ throughput │
├─────┼────────────┤
│ c4  │ 2,888 /s   │
│ c8  │ 5,215 /s   │
│ c16 │ 10,892 /s  │
│ c32 │ 16,019 /s  │
│ c64 │ 22,076 /s  │
└─────┴────────────┘
```

The large case is ~linear in the middle (2.9K → 5.2K → 10.9K is doubling per doubling of concurrency) and starts to flatten at c32→c64 (1.4×). The small case is non-monotonic: peak at c4/c8, then it falls.

The mechanism, from the code

Two facts in the code explain everything:

Fact 1 — each worker is a synchronous, closed-loop client. In  workload.rs  each worker gets its own TCP connection and loops:  recv(item)  → send query → block waiting for the full reply → record → repeat. So the number of requests in flight in the entire system is exactly  concurrency  (the channel only buffers work items, not responses). Nothing is pipelined.

Fact 2 — every cache operation takes one global mutex. In  cache.rs , the cache is a process-global  LazyLock<Mutex<Cache>> .  Read::execute  calls  filter_uncached  (locks, looks up, counts) and  insert  (locks again) — so even a pure cache hit acquires the single lock shared by all workers.

Why large ≈ linear

In the large case, ~51% of requests miss the cache and pay a real round trip — TCP send → server → Raft/storage read → reply — measured at p50 ≈ 1.4–1.5 ms. That is ~10,000× larger than the mutex critical section (~50 ns). Consequences:
1. The lock becomes irrelevant. Each worker holds the global lock for ~0.003% of its per-request time, so it's effectively uncontended — it stops being the bottleneck.
2. The bottleneck is now the network + servers, and the number of in-flight requests scales with concurrency. Since workers are closed-loop, throughput ≈  concurrency / round-trip time  while the servers are unsaturated. Double the concurrency → double the in-flight requests → roughly double the throughput. That's the linear region you see.
3. The flattening at c32→c64 is server saturation. As more requests pile up at the servers, queueing dominates — visible in the p50 rising from 1.4 ms (c4) to 2.9 ms (c64). That's exactly the M/M/m response-time growth, which is why the model fits this case.

Why small is not linear

In the small case, hit rate is 99.998% — only ~1,000 of ~30M+ requests ever touch the network (the CSVs show ~1,005–1,198 misses regardless of concurrency). So per-request time is almost entirely inside the process: lock → hashmap probe → unlock.

Here the single global mutex is the only resource, and a mutex cannot be parallelized — all workers queue for it. You get linear growth only up to the point where the lock is saturated (c4–c8 fills the pipeline gaps: channel, RNG, histogram recording). Past that, extra threads add nothing but contention: cache-line ping-pong on the lock word, futex sleep/wake syscalls, context switches. Per-request cost goes up, so total throughput goes down (c16 → 1.65M, c32 → 1.13M). The evidence is in the p50 column: 0.000511 ms (the histogram floor) at every concurrency level — the request never leaves the process, so there is no queueing to exploit.

The one-sentence answer

Throughput scales linearly with concurrency only when per-request time is dominated by a parallelizable, waiting-bound resource (network + servers: in-flight requests = concurrency,  throughput ≈ c/RTT ). When per-request time is dominated by a serialized, CPU-bound resource (one global cache mutex), concurrency buys you nothing and eventually hurts. Same code, same loop, same lock — the dataset size only decides which resource dominates, via the hit rate: fits-in-cache (s) → lock-bound; doesn't-fit (l) → queueing-bound.

Now I have the full server-side trace, grounded in the actual code. Here's how your worker's query gets processed once it leaves `workload.rs`.

## Where the client sends a query

In `src/bin/workload.rs`, two kinds of connections are made:

1. **`prepare` / `verify`** → always to `self.hosts[0]` (one node, the "controller").
2. **`execute` (the benchmark SELECTs)** → each of the `-c` workers opens its **own TCP session to one node**, round‑robin across your 5 hosts:
   - `Runner::run()` → `for addr in self.hosts.iter().cycle().take(self.concurrency)` → `Client::connect_timeout(addr, timeout)`.

So with `-c 64`, you have 64 separate node connections, spread across the 5 VMs. Each worker's `W::execute()` (Read workload) calls `client.execute(&query)` → `src/client.rs` → Bincode `Request::Execute` over TCP to whichever node it's connected to.

## What the receiving node does with it

Every node runs `src/server.rs::Server::serve()`, which listens on **960N (SQL)** and **970N (Raft)**, and routes messages through one central `raft_route()` loop (`server.rs:186`). The SQL path is:

1. `sql_accept()` (`server.rs:252`) accepts the TCP connection and spawns a **session thread** per client (`sql_session`, `server.rs:276`).
2. The session decodes `Request::Execute(query)` and runs it against a `sql::engine::Raft` engine (`sql_session` line 288).
3. The Raft engine is just a proxy: `Raft::request()` (`src/sql/engine/raft.rs:115`) puts a `(raft::Request, response_channel)` onto a crossbeam channel.
4. `raft_route()` (`server.rs:196-247`) picks it up, wraps it in a `Message::ClientRequest`, and **steps it into the local `raft::Node`** via `node.step(msg)`.

Now the **critical part** — what the node does next depends on whether it's the leader or a follower:

### If the receiving node is a **follower**
Per `src/raft/mod.rs:179` ("They are only processed on the leader, but followers will *proxy* them to the leader") and `docs/benchmark-flow-diagram.md:129-133`:
```
(4) receiving node executes the query
      - if follower: forward to Raft leader (internal)
      - leader executes read on local storage
      - rows returned to worker
```
The follower doesn't serve reads locally — every single one of your 5 nodes' incoming requests gets **forwarded to the one Raft leader**, regardless of which VM the client happened to reach.

### If the receiving node **is** the leader

This is the tab that makes your M/M/m unfit. From `src/raft/mod.rs:186-203` and `docs/architecture/raft.md:400-433`:

- toyDB has **no leader leases** ("the leader has to confirm with a quorum that it's actually still the leader").
- On read, the leader:
  1. Increments a read sequence number,
  2. Sends `Message::Read{seq}` to **all followers**,
  3. **Blocks until a quorum** — `cluster_size()/2 + 1 = 3` of 5 nodes — confirms with `ReadResponse{seq}` (`src/raft/node.rs:204-205`),
  4. Only then executes the actual read on its local `sql::engine::State` (`State::read`, `raft.rs:369`), which wraps a `Local` engine + MVCC/storage,
  5. Returns the rows as `Message::ClientResponse` back through the raft_route response channel → the SQL session thread → the worker's client.

So the full picture for your `SELECT id, value FROM "read" WHERE id = ...`:

```
worker(-c K)  --TCP-->  node X (sql :960_)
                         session thread
                              │ Raft::request()
                              ▼
                        raft_route → local Node.step(ClientRequest)
                              │
                (X is leader?)  ──no──> proxy ClientRequest → leader Y (raft :970_)
                              │(yes)
                              ▼
                        leader        sends Message::Read{seq} → followers
                              │
                              ▼  waits for quorum (3/5) ReadResponse seqs
                        execute read on leader's local SQL engine  ← the ONLY server
                              ▼
                        ClientResponse ──> the ORIGINAL client connection
```

## What this means for your M/M/m model

This single code walk-through is the **smoking gun** that explains why the M/M/m fit fails in every config. It definitively settles the open question from your first question (which was `m`?):

- **`m` is effectively 1, not `K` and not `5`.** Only the one elected leader executes reads. The other 4 nodes' replicas do *not* act as parallel servers — they only (a) proxy requests to the leader and (b) respond with quorum `Read` acks. There are no 5 server. So `m = K` over-predicts (it assumes 64 independent servers) and `m = 5` under-predicts (assumes 5).
- **Every read pays a mandatory extra RTT**: leader → followers → (quorum) → back, *before* the actual read latency. That's a fixed, per-request **network + quorum cost** added on top of DB service time. It is not part of `μ` and not in your Erlang-C `E[R]` formula.
- **`μ` from K=1 measures the wrong composite.** The K=1 no-cache run (497/s → ~2 ms/R) captures client→node→leader→...→quorum→leader→node→client, i.e. the round-trip you just traced, not the leader's local service rate. That inflated "service time" is why the saturation knee of the M/M/m prediction sits nowhere near your measured, cache-amplified curve.

So the empirically-sound model for this codebase is roughly:

```
E[R](k,p) = R_roundtrip(client→node→leader→quorum→leader→client)
          + (1 - H) × R_execute   (+ cache-latency on hit)
```

where `R_execute` is the leader-local storage read (≈ the ~0.14 ms you get at high K), not the K=1 composite. That, plus a hit rate term, is what you should fit against `csv/p2/exp3` — and it will fail differently on the `l/*` vs `s/*` configs precisely because the `s` dataset is ~99.99% cache hit (`csv/p2/exp3/c4/s/...` shows 54 M txns/s, 0.99998 hit) while `l` is ~50% hit.

If you'd like, I can (in Act mode) turn this into a compact pipeline that derives `R_local` from the saturated no-cache runs, plugs in the per-run `cache_hit_rate` from your summaries, and prints measured-vs-predicted residuals for each of `m = K`, `m = 1`, and `m = 1 + quorum-RTT` so we can see which assumption closes the gap. Want me to proceed with that?

Short answer: **that situation can't happen in this system.** There's no "row lives on one node" concept — every node holds a complete copy of the entire dataset. So the leader always has every row; the read is always satisfied locally on it.

Here's the evidence from the code, in case you want to confirm it yourself:

## toyDB does not shard/partition rows

`src/raft/mod.rs:30-34` says it explicitly:
> "each node stores a **complete copy of the entire dataset** … Raft does not provide horizontal scalability … by **sharding the data into multiple Raft clusters** … this is **out of scope here**."

`docs/architecture/sql-raft.md:4`: *"All nodes will store a **full copy** of the SQL database."*

And in the write path, every node applies each write to its own local engine (`docs/cluster-cache-diagram.md` line 104-106: *"every node applies the write to its own storage engine"*), not just the leader. So row replication is 100% — there is no partitioning, no hash routing to a "owner" node.

## So what the leader actually does on your `SELECT`

The whole `read` table (all 1000 or 10000 `(id, value)` rows) is replicated to **all 5 nodes** during `workload.prepare()`. When your query arrives:

1. The leader has *already* applied every `INSERT` locally (via the Raft log, on all nodes).
2. Your `SELECT ... WHERE id = X` compiles to a `Read::Get { table, ids }` command (`src/sql/engine/raft.rs:220-223`).
3. The leader executes it against its own local engine: `Read::Get` → `self.local.resume(txn)?.get(&table, &ids)` (`raft.rs:380-382`) — a plain local key-value / index lookup in the leader's own Bitcask/MVCC storage (`src/sql/engine/local.rs`).

There's no round-trip to fetch a row "from another node" — the row is in the leader's own storage engine, so it reads it directly.

## Why your mental model is off (and it matters for the benchmark)

You're picturing a **sharded** architecture (Cassandra, MySQL Cluster, Redis Cluster) where a row is owned by one node and reads route to it. toyDB is the **replicated + single-leader** model:

| | Sharded (your assumption) | toyDB (actual) |
|---|---|---|
| Where does a row live? | one owner node | every node (full copy) |
| Where do reads execute? | route to the owner | always the one Raft leader |
| Can reads parallelize across 5 nodes? | yes | no |

This is exactly why your M/M/m fit breaks: the **5 nodes are not 5 parallel servers for reads**. They all hold the data, but only the leader serves queries (and even then, after a quorum-ack round-trip). The other 4 nodes just replicate the dataset and answer `Read` heartbeats — they contribute *nothing* to read throughput. Hence effective `m ≈ 1` (the leader), which neither `m = K` nor `m = 5` captures.

If you *wanted* sharding (so different nodes genuinely own different rows and reads truly parallelize), that's a different architecture entirely — which is out of scope for this codebase, as the raft module documentation notes. For your benchmarking/M/M/m investigation, the takeaway stands: model the whole cluster as **one server (the leader) plus a fixed quorum/network overhead**, not K or 5 parallel servers.

# What can I do next to prove
Extracting numeric model predictions from the shell is being flaky in this plan mode, so I'll ground the proof in the numbers I already pulled directly from your CSVs, and give you a concrete set of experiments to run on the deployed cluster. Here's what to do.

## Two numbers you already have that half-prove it

For `l/uniform` (10k rows, no-cache):

- **μ from K=1 ≈ 497 /s** → E[R] ≈ 2.0 ms
- **measured K=64 no-cache ≈ 7,141 /s** → per-request service at saturation ≈ 0.14 ms

Two consequences you can state directly:
1. **μ is not a stable "service rate."** It's 14× *higher* when derived at saturation than when derived at K=1. K=1 measures client→node→leader→quorum→leader→node round-trip, not the leader's local service. That alone violates the M/M/m premise of a fixed μ.
2. **Even `m=5` can't reach the measurement.** A closed M/M/m with 5 servers and μ=497 tops out at **5×497 = 2,485 /s** as K→∞, but you measured 7,141 /s at K=64. So *no* m with your K=1 μ reproduces the data — the μ source is the bug, and the only interpretation that fits is "1 leader at ~7,141 /s" plus a network/quorum term.

Then add the cache confounder from the same data:
3. `s/uniform` (1k rows) cached = ~1.8 M txns/s at **0.99998 cache-hit**. The cache, not the cluster, is what dominates the cached curve — another reason the fit fails on `csv/p2/exp3`.

## Experiments to *prove* it on the deployed cluster (most decisive first)

For a clean proof, run these in **no-cache mode** (cache masks the effect), `l/uniform`, 30s each, K=64, 5 runs.

**1. Leader-only vs spread — discriminates m=1 vs m=5.**
Find the leader (a `status` query, or read the leader from `request_leader` test / the leader's node logs), then run the workload twice:
- all `-c 64` workers connected **only to the leader** (`-H leader:960N`)
- `-c 64` spread across all 5 (`-H 10.0.0.2:9601,...,10.0.0.4:9605`)

If reads are leader-executed, throughput is **~equal** (same leader does all the work). If the 5 nodes were genuinely parallel servers, the spread run would beat leader-only by up to 5×.
→ Expected result: roughly equal → proves single-leader serialization.

**2. All-workers-on-one-follower — proves proxying.**
Connect all 64 workers to a **single follower**. If the follower forwards every read to the leader, throughput ≈ the leader-only run (just one extra hop). If reads ran locally, this would be near `1/4` of the leader run, not equal.
→ Expected: ≈ leader-only → proves follower→leader forwarding.

**3. CPU profile per node — physical evidence of one-busy-node.**
During a run, sample every VM:
```
gcloud compute ssh "$NODE-node-$i" --zone "$ZONE" -- "pidstat -p \$(pgrep toydb) 1 5"
```
→ Expected: the **leader's toydb CPU is high**, the 4 followers' toydb CPU is near idle (they only proxy and answer Read acks). If reads parallelized, all 5 would show comparable CPU.

**4. Packet capture — proves the per-read quorum round-trip.**
On the leader:
```
sudo tcpdump -nn -i any 'portrange 9701-9705'
```
while a read benchmark runs. → Expected: **every read generates `Read{seq}` → 4 followers → `ReadResponse`** traffic before the result. That's the per-request RTT your Erlang-C formula is missing (no leader lease in toyDB, confirmed in `src/raft/mod.rs:186-203` and `docs/architecture/raft.md:400-433`).

**5. Scale past the ceiling — cleanest M/M/m discriminator.**
Run no-cache at **K = 64, 128, 256** (same config). Closed M/M/m predicts throughput → **m·μ** as K→∞. So:
- if reads are 1 leader, throughput **plateaus near ≈7,141 /s** (your K=64 value)
- if it were really 5 servers, it would keep climbing toward ≈5× a true μ.

→ Expected: plateau ≈ your K=64 number → single-leader ceiling confirmed.

## Data-only analyses on `csv/p2` you can add

- **Residual table**: compute `predicted/measured` for `m=K`, `m=5`, and `m=1` against the **no-cache** series, and report which `m` gives residuals nearest 1.0 (I'd expect `m=1` with the saturated μ). This turns the code walk-through into a number.
- **μ-sensitivity**: print μ from c1 vs μ from c64 — the ~14× gap quantifies "K=1 measures round-trip, not service."
- **Cache decomposition**: fit `E[R] = H·R_cache + (1−H)·R_db` using the per-run `cache_hit_rate` column (already in your summaries) and show it closes the `l` (≈50% hit) vs `s` (≈100% hit) gap — isolating the cache confounder from the m/miscount confounder.
- **CV check**: from your p50/p90/p99/max (e.g. l/uniform c64 no-cache: p50≈8 ms, p90≈13, p99≈19, max≈68) — service time has high variability, so the `M` (=exponential/Poisson) assumption is also violated. Suggests M/G/m or a closed-form with a measured CV.

## What I'd implement (only in Act mode)

I could add a `plot/modelling/prove-leader-model.py` that automates the residuals + μ-sensitivity + cache-decomposition tables against `csv/p2`, and small runner scripts for experiments 1–5 above. I'm in Plan mode so I haven't changed anything. Toggle to **Act mode** and I'll build it.