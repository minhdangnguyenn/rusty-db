Use a closed, finite-client model—not `M/M/m` with `m =` client concurrency.

For the no-cache, read-only benchmark, the closest simple model is:

\[
closed M/G/1//K
\]

(the machine-repairman / finite-source model): `K` synchronous workers circulate requests through one dominant leader-side bottleneck, with general—not exponential—service time. If you need predictive accuracy, use a calibrated discrete-event simulation or a closed queueing network rather than one Kendall model.

Why:

- `K` is the number of benchmark clients, not parallel database servers. Each worker sends one request, waits, then sends its next request. [workload.rs](/home/minh/repo/rusty-db/src/bin/workload.rs:168)
- Although each SQL connection gets a thread, every node’s requests enter one Raft routing loop; follower requests ultimately converge on the single leader. [server.rs](/home/minh/repo/rusty-db/src/server.rs:234)
- A linearizable read waits for a quorum confirmation, then the leader drains ready reads serially through `state.read`. [node.rs](/home/minh/repo/rusty-db/src/raft/node.rs:906) [node.rs](/home/minh/repo/rusty-db/src/raft/node.rs:1034)
- Therefore, five replicas improve fault tolerance and provide quorum responses; they do not create five independent read-execution servers.

The existing model is conceptually invalid because it explicitly sets `m = K`. That makes the predicted capacity grow whenever more clients are added, rather than modelling a fixed system capacity. [exp3-modelling-diagram.md](/home/minh/repo/rusty-db/docs/exp3-modelling-diagram.md:49)

Why plain `M/M/1` also does not fit:

1. It assumes open Poisson arrivals. Your benchmark is closed-loop: arrivals are throttled by completed responses.
2. It assumes exponential, independent, fixed service times. Here a request includes TCP, possible follower forwarding, a quorum round trip, leader scheduling, and storage.
3. K=1 latency is largely quorum/network delay which can overlap across concurrent requests. It must not be treated as serialized leader service time. The saved no-cache runs show about 470–500 req/s at K=1 but thousands of req/s at higher K—evidence of overlap/pipelining.
4. Cache-enabled runs are not database-request measurements: a hit sends no SQL request, and all workers contend on one process-global `Mutex<Cache>`. [workload.rs](/home/minh/repo/rusty-db/src/bin/workload.rs:434) [cache.rs](/home/minh/repo/rusty-db/src/cache/cache.rs:95) The hit/miss sequence is stateful, so it is neither Poisson nor independent.

A good report explanation is:

> The M/M/m model did not fit because its server count was incorrectly equated with client concurrency. ToyDB routes all linearizable reads through a single Raft leader and requires quorum confirmation. The workload is a closed population of synchronous clients, while request latency consists of overlapping network/quorum delays and leader-side serialized work. In cache-enabled experiments, measured transactions are additionally a state-dependent mixture of local cache hits and database misses. Hence the assumptions of Poisson arrivals, exponential independent service, and fixed parallel servers do not hold.

Practical methodology:

- Fit **no-cache reads** separately using closed `M/G/1//K`; estimate the leader’s service distribution from leader-side instrumentation, not `K=1` end-to-end throughput.
- Instrument timestamps for: SQL receive, leader admission, quorum-ready, `state.read` completion, and response sent. This separates queueing from quorum delay.
- For cache experiments, report a separate two-path closed network: cache hit path versus miss path to the leader, using measured hit ratio. Do not claim a single M/M model covers it.
- Model writes separately: they have log replication, quorum commit, and state-machine application, so they are a different service class.