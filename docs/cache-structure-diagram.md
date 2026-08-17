# Cache Structure and Implementation (`src/cache/cache.rs`)

The cache is a **client-side, process-global singleton** in the benchmark
loader: a single `Cache` behind one `Mutex`, shared by all K workers. It
stores `id -> value` pairs of the `"read"` table so repeated lookups never
touch the database.

## 1. Where the cache lives

```
Benchmark loader process (src/bin/workload.rs)
  +--------------------------------------------------------------+
  | worker 1     worker 2   ...   worker K                       |
  |   |             |               |                            |
  |   +-------------+---------------+                            |
  |                 v                                            |
  |  cache::filter_uncached(keys)   /   cache::insert(key, value)|
  |                 |                                            |
  |                 v                                            |
  |  static CACHE: LazyLock<Mutex<Cache>>   (src/cache/cache.rs) |
  |  +--------------------------------------------------------+  |
  |  | Cache {                                               |   |
  |  |   entries: HashMap<u64, CacheEntry>   (key -> node)   |   |
  |  |   head:    Option<u64>   (MRU end of the list)        |   |
  |  |   tail:    Option<u64>   (LRU end of the list)        |   |
  |  | }                                                    |    |
  |  +--------------------------------------------------------+  |
  +--------------------------------------------------------------+
```

The lock is taken **only** for the map/list operations (nanoseconds), and is
released while the worker performs the SQL round-trip. That is why the single
global mutex is not the bottleneck for the network-bound (large dataset)
case - the critical section is ~0.003% of each request.

## 2. Internal data structure

A `HashMap<u64, CacheEntry>` plus an **intrusive doubly-linked list** for
ordering (head = MRU, tail = LRU). `prev`/`next` store `u64` keys, not
pointers, so lookup stays O(1) and no extra nodes are allocated.

```
Internal structure: HashMap + intrusive doubly-linked list
========================================================================
  +------------------------------------------------------------------+
  | entries: HashMap<u64, CacheEntry>                               |
  |                                                                  |
  |   7 -> CacheEntry { value: String, prev: None,    next: Some(3) }|
  |   3 -> CacheEntry { value: String, prev: Some(7), next: Some(9) }|
  |   9 -> CacheEntry { value: String, prev: Some(3), next: Some(5) }|
  |   5 -> CacheEntry { value: String, prev: Some(9), next: None    }|
  |                                                                  |
  |   head: Option<u64> = Some(7)     (MRU end)                      |
  |   tail: Option<u64> = Some(5)     (LRU end)                      |
  +------------------------------------------------------------------+

  The same 4 entries as a doubly-linked list:

    head (MRU)                                                  tail (LRU)
      |                                                             |
      v                                                             v
  +--------+      +--------+      +--------+      +--------+
  | key  7 | <--> | key  3 | <--> | key  9 | <--> | key  5 |
  +--------+      +--------+      +--------+      +--------+

  prev/next store u64 keys, not pointers - the list is intrusive,
  so lookup is O(1) via the HashMap and no extra nodes are allocated.
```

## 3. Operations

```
read path:  filter_uncached(&HashSet<u64>) -> Vec<u64>
  +------------------------------------------------------------------+
  |  lock the global Mutex                                           |
  |    for each key:                                                 |
  |      entries.contains_key(key) ?                                 |
  |        yes -> HITS += 1                                          |
  |               if LRU: detach(key), attach_to_front(key)          |
  |        no  -> MISSES += 1, push key to uncached                  |
  |  unlock                                                          |
  |  return uncached keys - the caller SELECTs only these            |
  +------------------------------------------------------------------+

write path:  insert(key, value)
  +------------------------------------------------------------------+
  |  lock the global Mutex                                           |
  |    key already in entries ?                                      |
  |      yes -> update entry.value                                   |
  |             if LRU: detach(key), attach_to_front(key)            |
  |      no  -> entries.insert(key, {value, prev: None, next: None}) |
  |             attach_to_front(key)                                 |
  |    entries.len() > max_size ?                                    |
  |      -> victim = pop_tail()      (tail = LRU or FIFO end)        |
  |         entries.remove(&victim)                                  |
  |  unlock                                                          |
  +------------------------------------------------------------------+
```

Workflow per work item: `filter_uncached` (lock, check, unlock) -> only for
the misses run `SELECT` over the network -> `insert` each returned row
(lock, store, maybe evict, unlock). Hits never touch the database.

## 4. Eviction: LRU vs FIFO

`EvictType` is an atomic `u8`: `LRU = 0` (default) or `FIFO = 1`
(`--fifo`). The only difference is whether a **hit reorders** the list;
eviction always removes the tail.

```
max_size = 3, insert order: A, B, C
initial list (head -> tail):  C <-> B <-> A

hit on A:
  LRU : A <-> C <-> B        (A moved to the MRU end)
  FIFO: C <-> B <-> A        (no reorder on hit)

insert D (cache full -> evict tail):
  LRU : D <-> A <-> C        (B evicted: least recently used)
  FIFO: D <-> C <-> B        (A evicted: oldest inserted)
```

- **LRU**: frequently accessed keys keep moving to the head and never become
  the eviction victim; good when access is skewed (e.g. zipf).
- **FIFO**: entries age out by insertion order regardless of access.

## 5. Config and stats

Global atomics (no locking needed to read them):

| Static | Default | Purpose |
|---|---|---|
| `ENABLED` | false | cache on/off (set by `--cache`) |
| `MAX_SIZE` | 5000 | max entries (`--cache-size`) |
| `EVICT_TYPE` | LRU | eviction policy (`--fifo`) |
| `HITS` / `MISSES` | 0 | counters, read by `stats()` |

| Function | Effect |
|---|---|
| `enable()` / `is_enabled()` | toggle the cache |
| `set_max_size(n)` | change the max size |
| `set_eviction(EvictType)` | LRU or FIFO |
| `filter_uncached(&HashSet<u64>)` | batch lookup, counts hits/misses, LRU reorder |
| `insert(key, value)` | store/update, evict tail when full |
| `stats() -> (hits, misses, ratio)` | hit rate = `hits / (hits + misses)` |
| `reset_stats()` | zero counters at the start of a run |
