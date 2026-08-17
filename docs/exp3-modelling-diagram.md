# Exp3 - SQL Flow Through Concurrent Workers (M/M/m Modelling)

Exp3 measures how throughput and response time scale with **concurrency K**
(`-c` flag) and fits the results with a **closed M/M/m queueing model**.
Everything below is based on `src/bin/workload.rs` and
`plot/modelling/mmm-throughput.py`.

## 1. Closed-loop worker flow

```
benchmark loader - K concurrent workers (K = 4 / 8 / 16 / 32 / 64)
  +----------------------------------------------------------------------+
  | worker 1    worker 2   ...   worker K                                |
  |   (1)          (1)              (1)     generate key batch           |
  |   (2)          (2)              (2)     filter_uncached()            |
  |   (5)          (5)              (5)     cache::insert + record       |
  | (shared client cache behind one global Mutex)                        |
  +----+------------+--------------+-------------------------------------+
       |            |              |
       |            |              |
       +------------+--------------+
                    |
                    |  (3) SQL SELECT  (one TCP connection per worker)
                    v
  +----------------------------------------------------------------------+
  | 5-node cluster (GCP VMs)                                             |
  | node SQL port -> (follower forwards) -> Raft leader executes         |
  | the read on its storage engine; each VM keeps a full copy            |
  +----------------------------------------------------------------------+
                    |  (4) reply on the same connection
                    v

  closed loop: (1) -> (2) -> (3) -> (4) -> (5) -> next work item -> (1)
  the worker blocks at (3) until the reply arrives, so exactly K
  requests are in flight at all times (nothing is pipelined).

  (3) and (4) happen over the network (worker <-> cluster), so they are
  drawn outside the worker box. (5) is back in the worker: it writes the
  returned rows into the client-side cache (cache::insert) and records
  the latency. Without (5) the cache would never be filled, and every
  request would miss.
```

Each worker is a synchronous, closed-loop client: generate a batch of keys,
filter the cache, send one SQL query, block for the full reply, record
latency, repeat. There is no pipelining, so **in-flight requests = K** always,
and Little's law holds: `K = X * R` (throughput x response time).

## 2. The M/M/m model of the cluster

The whole cluster (5 nodes + network + leader round-trips) is abstracted as a
**single queueing center with m servers**, where `m = K` (the concurrency
level). The K workers are the jobs circulating in the closed loop.

```
  K workers                         M/M/m center (m = K)
  (jobs in the system)   +-------------------------------------+
        |                |                                     |
        +-- lambda ----> |  [ queue ] -----> [ m servers ]     |
        |                |    wait W            service 1/mu   |
        |                |                                     |
        |  X <-----------+-- departures (completed requests)   |
        |                                                     |
        +-- closed loop: every departure immediately becomes
            a new arrival -> exactly K jobs stay in the system
```

Model formulas (as implemented in `plot/modelling/mmm-throughput.py`):

```
 utilization      rho = lambda / (m * mu)
 Erlang-C         C(m, rho) = probability a request has to wait in queue
 mean response    E[R] = (1 / mu) * ( 1 + C(m, rho) / (m * (1 - rho)) )
 throughput       X = K / E[R]            (Little's law, closed loop)
```

The model solves the closed-loop fixed point by bisection: find the arrival
rate lambda such that `X = K / E[R]`; that `X` is the predicted throughput.

| Symbol | Meaning                         | Where it comes from                                                   |
| ------ | ------------------------------- | --------------------------------------------------------------------- |
| K      | concurrency = number of workers | `-c` flag: 4, 8, 16, 32, 64                                           |
| m      | servers in the model            | `m = K` (plot x-axis: "Concurrency level (K = m)")                    |
| mu     | service rate [req/s]            | estimated from **K=1 no-cache** runs: `mu = 1 / mean(1 / throughput)` |
| lambda | arrival rate [req/s]            | solved so the closed loop balances (`X = K / E[R]`)                   |
| E[R]   | mean response time              | Erlang-C formula above                                                |
| X      | throughput [txns/s]             | measured vs predicted vs no-cache baseline                            |

## 3. Modelling dataflow (where each number comes from)

```
  csv/p2/exp3-no-cache/c1/{s,l}/{uniform,zipf}     csv/p2/exp3/{c4..c64}/{s,l}/{uniform,zipf}
  (K = 1, no cache, 5 runs each)                   (cache ON, K = 4..64, 5 runs each)
        |                                                   |
        v                                                   v
  mean service time = mean(1 / throughput)            mean throughput + 95% CI
        |                                                   |
        v                                                   |
  mu = 1 / mean service time                                |
        |                                                   |
        +----------------------------+----------------------+
                                     v
        closed M/M/m model: X_pred(K) = fixed point of X = K / E[R]
                                     |
                                     v
        charts (plot/modelling/mmm-throughput.py, mmm-responsetime.py)
        throughput & response time vs concurrency K
        curves:  measured (red)  vs  M/M/m predicted (green)
                 vs  no-cache baseline (black, csv/p2/exp3-no-cache/c4..c64)
```

Why this model fits: at low K the system is unsaturated, the queue is empty
(`C ~ 0`), so `E[R] ~ 1/mu` and throughput grows roughly linearly with K
(`X ~ K * mu`). As K grows, utilization `rho` approaches 1, the Erlang-C
queueing term explodes, response time grows, and throughput flattens - the
classic M/M/m saturation curve.

## 4. Exp3 parameters

| Parameter       | Value                           | Meaning                                 |
| --------------- | ------------------------------- | --------------------------------------- |
| `-c` (K)        | 4, 8, 16, 32, 64                | concurrency = workers = model's m       |
| `--rows`        | 1000 (s) / 10000 (l)            | dataset size (fits cache / doesn't fit) |
| `--dist`        | uniform / zipf                  | key access distribution                 |
| `--cache`       | on (exp3) / off (exp3-no-cache) | client-side cache                       |
| runs per config | 5 (`--id 1..5`)                 | 95% CI via t-distribution               |
| `--duration`    | 30 s                            | run length per run                      |
| `mu` source     | `exp3-no-cache/c1`              | service rate from single-request runs   |
