# Cache Architecture

## 5-Node Cluster — Cache in the Middle

```mermaid
flowchart TD
    CACHE["In-Memory Cache<br/>5,000 entries<br/>LRU / FIFO eviction"]

    N1["Node 1<br/>SQL 9601 | Raft 9701"]
    N2["Node 2<br/>SQL 9602 | Raft 9702"]
    N3["Node 3<br/>SQL 9603 | Raft 9703"]
    N4["Node 4<br/>SQL 9604 | Raft 9704"]
    N5["Node 5<br/>SQL 9605 | Raft 9705"]

    S1["Storage 1<br/>(B-tree on disk)"]
    S2["Storage 2<br/>(B-tree on disk)"]
    S3["Storage 3<br/>(B-tree on disk)"]
    S4["Storage 4<br/>(B-tree on disk)"]
    S5["Storage 5<br/>(B-tree on disk)"]

    CLIENT["Benchmark Client<br/>Workload Workers (round-robin)"]

    CLIENT --> N1 & N2 & N3 & N4 & N5

    N1 <--> CACHE
    N2 <--> CACHE
    N3 <--> CACHE
    N4 <--> CACHE
    N5 <--> CACHE

    CACHE --- S1 & S2 & S3 & S4 & S5

    N1 <--> N2 <--> N3 <--> N4 <--> N5
```

Each node owns one cache instance. On a cache miss, the node queries its local storage engine, then populates the cache for subsequent requests.

## Per-Node Query Path

```mermaid
flowchart TB
    subgraph NODE["toyDB Node"]
        SQL["SQL Listener (port 960x)"]

        RAFT["Raft Layer<br/>Consensus & Replication"]

        CACHE["In-Memory Cache<br/>• Max 5,000 entries<br/>• Eviction: LRU or FIFO<br/>• On hit → return immediately"]

        STORAGE["Storage Engine<br/>B-tree on disk"]

        SQL --> RAFT
        RAFT --> CACHE

        CACHE -- Cache Hit --> RESPONSE["Return to client"]

        CACHE -- Cache Miss --> STORAGE
        STORAGE --> POPULATE["Insert into cache"]
        POPULATE -.-> CACHE
        POPULATE --> RESPONSE
    end

    CLIENT_REQ["Client Request"] --> SQL
```

## Cache Flow

```mermaid
flowchart LR
    REQ["Read(id=X)"] --> CHECK{"In cache?"}
    CHECK -- Yes --> HIT["Return cached value<br/>(fast, no I/O)"]
    CHECK -- No --> MISS["Query storage engine"]
    MISS --> INSERT["Insert into cache<br/>(evict if full)"]
    INSERT --> RESP["Return value<br/>to SQL layer"]
    HIT --> DONE
    RESP --> DONE
```

## Cache Eviction Policies

```mermaid
flowchart TB
    EVICT{"Cache full?"}

    EVICT -- Yes --> POLICY{"Eviction policy"}

    POLICY -- LRU --> LRU_EVICT["Remove<br/>Least Recently Used<br/>entry"]
    POLICY -- FIFO --> FIFO_EVICT["Remove<br/>First In, First Out<br/>entry"]

    LRU_EVICT --> INSERT_NEW["Insert new entry"]
    FIFO_EVICT --> INSERT_NEW
    EVICT -- No --> INSERT_NEW
```

## Key Design Points

| Aspect | Detail |
|--------|--------|
| **Cache location** | In-process, each node maintains its own cache (no distributed cache) |
| **Cache capacity** | 5,000 entries |
| **Eviction policies** | LRU (default) or FIFO, configured via `--fifo` flag |
| **On miss** | Value is read from the B-tree storage, inserted into cache, then returned |
| **Concurrent access** | Workers connect round-robin across all 5 nodes; the per-node cache is shared across all connections to that node |
| **Read-only workload** | All benchmark operations are reads; writes only occur during the initial data load |
