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

┌─────┬──────────────┐
│ c   │ throughput   │
├─────┼──────────────┤
│ c4  │ 1,761,341 /s │
│ c8  │ 1,727,893 /s │
│ c16 │ 1,654,749 /s │
│ c32 │ 1,127,480 /s │
│ c64 │ 1,438,652 /s │
└─────┴──────────────┘

Large dataset, cache (rows=10000, uniform) — hit rate ≈ 49–50%:

┌─────┬────────────┐
│ c   │ throughput │
├─────┼────────────┤
│ c4  │ 2,888 /s   │
│ c8  │ 5,215 /s   │
│ c16 │ 10,892 /s  │
│ c32 │ 16,019 /s  │
│ c64 │ 22,076 /s  │
└─────┴────────────┘

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