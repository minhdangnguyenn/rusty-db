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