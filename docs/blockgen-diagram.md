# BlockGen - Work Item Generation (`src/bin/workload.rs`)

`BlockGen` is the iterator that produces work items for the read workload.
Every call to `next()` returns one work item: a `HashSet<u64>` containing a
batch of row IDs from the `"read"` table to look up. It intentionally
alternates between **fresh** IDs (never used before) and **reused** IDs
(random samples of already-seen IDs) in fixed-size blocks.

## 1. Flow of `BlockGen::next()`

```
BlockGen::next() - one call returns one work item (one batch)
========================================================================
        |
        v
  +--------------------------------------------------------+
  | (1) end of current block?  (block_remaining == 0)      |
  |       yes -> flip is_fresh_block (fresh <-> reused)    |
  |              block_remaining = block_size              |
  |       no  -> keep the current block type               |
  +--------------------------------------------------------+
        |
        v
  +--------------------------------------------------------+
  | (2) n = min(batch, block_remaining)                    |
  |     block_remaining -= n                               |
  +--------------------------------------------------------+
              |                               |
              |                               |
              +-------------------------------+
  +------------------------+      +------------------------+
  | (3a) FRESH block       |      | (3b) REUSED block      |
  | for each of n IDs:     |      | for each of n IDs:     |
  |   if fresh_keys left:  |      |   pick randomly from   |
  |     take fresh_keys[   |      |   used_keys:           |
  |     fresh_idx],        |      |     uniform            |
  |     fresh_idx += 1,    |      |     or zipf (skew)     |
  |     push id to         |      |                        |
  |     used_keys          |      |                        |
  |   else: sample from    |      |                        |
  |     used_keys          |      |                        |
  +------------------------+      +------------------------+
              |                               |
              |                               |
              +-------------------------------+
                              |
                              v
                              return HashSet<u64> of n IDs (no duplicates)
```

Notes:

- `fresh_keys` is built once in `generate()` as `shuffle(1..=rows)`, so fresh
  IDs are handed out in random order, never repeated.
- When `fresh_keys` runs out (all `rows` IDs have been used once), fresh
  blocks fall back to sampling from `used_keys` like reused blocks.
- `HashSet` guarantees no duplicate IDs within a single work item.

## 2. How the workload uses BlockGen

```
Usage in Runner::run()
========================================================================
  +------------------------------------------------------------+
  | (a) generate(): fresh_keys = shuffle(1..=rows)             |
  |     returns BlockGen { batch, block_size, rng,             |
  |       fresh_keys, fresh_idx, used_keys, ... }              |
  +------------------------------------------------------------+
        |
        v
  +------------------------------------------------------------+
  | (b) generator thread (spawned by Runner::run):             |
  |     for item in BlockGen {         // unlimited            |
  |         if stop { break }          // --duration           |
  |         work_tx.send(item)         // 1 item = 1 batch     |
  |     }                                                      |
  +------------------------------------------------------------+
        |   work_tx: bounded channel, capacity = concurrency K
        v
  +------------------------------------------------------------+
  | (c) K workers (one thread each, own TCP connection):       |
  |     while let Ok(item) = work_rx.recv() {                  |
  |         Read::execute(client, &item)                       |
  |             // filter_uncached -> SELECT -> cache::insert  |
  |         recorder.record(latency)   // HDR histogram        |
  |     }                                                      |
  +------------------------------------------------------------+
```

- The generator iterates `BlockGen` **forever**; it only stops when the
  `--duration` deadline is reached (`stop` flag) or the channel closes.
- `--count` is **not** a limit here - it is only written to the CSV summary
  and passed to `verify()`.
- Each item is one batch of IDs; the worker turns it into one
  `SELECT ... WHERE id = ... OR id = ...` query (only for cache misses).

## 3. Block timeline example

```
Example: rows = 1000, batch = 1, block_size = 100
(each work item = 1 ID; each block = 100 work items)

 item     1..100        item 101..200       item 201..300     ...
 block 1  FRESH         block 2 REUSED      block 3 FRESH     ...
 IDs:     first 100     random from the     next 100 unused
          unused IDs    100 used IDs        IDs
          (shuffled)                        (shuffled order)
 effect:  cache miss    cache hit           cache miss

 ... until all 1000 fresh IDs have been used (10 fresh blocks) ...
 afterwards every block samples randomly from the full 1000 used_keys:
   uniform -> every ID equally likely
   zipf    -> a few "hot" IDs chosen very frequently (skew 1.0)
```

## 4. Fields and defaults

| Field | Default (CLI flag) | Role |
|---|---|---|
| `batch` | 1 (`--batch`) | number of IDs per work item |
| `block_size` | 100 (`--block-size`) | IDs per block before flipping fresh <-> reused |
| `fresh_keys` | `shuffle(1..=rows)` | pool of never-used IDs |
| `fresh_idx` | 0 | next position in `fresh_keys` |
| `used_keys` | `[]` | IDs already handed out (source for reused blocks) |
| `block_remaining` | `block_size` | IDs left in the current block |
| `is_fresh_block` | `true` | current block type |
| `use_zipf` / `zipf_skew` | `uniform` / `1.0` (`--dist`, `--zipf-skew`) | sampling distribution for reused blocks |

## 5. Why the alternation matters

- **Fresh blocks** force cache **misses** (IDs never seen), which fill the
  client-side cache via `cache::insert()`.
- **Reused blocks** force cache **hits** on already-seen IDs.
- Combined with `zipf` skew, this is what produces the measured hit rates:
  ~49-50% for the large dataset (`l`, rows=10000) and ~99.99% for the small
  dataset (`s`, rows=1000), as seen in the experiment CSVs.
