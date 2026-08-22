# GenBlock Flow (corrected) — reference for redrawing

This is the verified-correct flow of `BlockGen::next()` (`src/bin/workload.rs:491`),
matching the code. Use it to redraw the diagram in draw.io.

## Full flow (ASCII)

```
               ┌─────────────────────────┐
               │  End of current block ? │   block_remaining == 0
               └────────────┬────────────┘
                 Yes        │        No
          ┌─────────────────┴─────────────────┐
          ▼                                   ▼
┌──────────────────────────┐      ┌─────────────────────────┐
│ Flip block type          │      │ Keep the current block  │
│ (fresh ↔ reused)         │      │ type                    │
│ reset block_remaining=100│      │                         │
└─────────────┬────────────┘      └────────────┬────────────┘
              └───────────────┬────────────────┘
                              ▼
               ┌───────────────────────────────────────┐
               │ Chunk the batch so it will not cross  │
               │ the block remaining                   │
               │ n = min(batch, block_remaining)       │
               │ block_remaining -= n                  │
               └───────────────────┬───────────────────┘
                     fresh         │         reused
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
┌──────────────────────────┐              ┌──────────────────────────┐
│ Fresh Block:             │              │ Reused Block:            │
│ hand out never seen keys │              │ sample already seen keys │
│  fresh keys left?        │              │  uniform or zipf(skew)   │
│    yes → take next key   │              │  from used_keys          │
│          (1st access ⇒   │              │                          │
│           cache miss)    │              │                          │
│          push to         │              │                          │
│          used_keys       │              │                          │
│    no → sample from      │              │                          │
│          used_keys       │              │                          │
└─────────────┬────────────┘              └────────────┬─────────────┘
              └──────────────────┬─────────────────────┘
                                 ▼
                ┌──────────────────────────────────┐
                │ Return work item (HashSet of n)  │
                └────────────────┬─────────────────┘
                                 ▼
               ┌─────────────────────────┐
               │  Stop Flag (30s) set ?  │
               └────────────┬────────────┘
                 Yes        │        No
              ┌─────────────┴─────────────┐
              ▼                           ▼
   ┌─────────────────────┐     loop back to
   │ Stop the benchmark  │     "End of current block ?"
   └─────────────────────┘     (call next() again)
```

## Box texts (copy-paste into draw.io)

| Shape | Text |
|---|---|
| diamond | `End of current block ?` |
| box | `Flip block type (fresh ↔ reused)` + newline + `reset block_remaining = 100` |
| box | `Keep the current block type` |
| box | `Chunk the batch so it will not cross the block remaining` |
| box | `Fresh Block: hand out never seen keys` |
| box | `Reused Block: sample already seen keys` |
| box | `Return work item (HashSet of n ids)` |
| diamond | `Stop Flag (30s) set ?` |
| box | `Stop the benchmark` |

## Edges (with branch labels)

| From | To | Label |
|---|---|---|
| End of current block ? | Flip block type ... | **Yes** |
| End of current block ? | Keep the current block type | **No** |
| Flip block type ... | Chunk the batch ... | — |
| Keep the current block type | Chunk the batch ... | — |
| Chunk the batch ... | Fresh Block ... | **fresh** |
| Chunk the batch ... | Reused Block ... | **reused** |
| Fresh Block ... | Return work item ... | — |
| Reused Block ... | Return work item ... | — |
| Return work item ... | Stop Flag (30s) set ? | — |
| Stop Flag (30s) set ? | Stop the benchmark | **Yes** |
| Stop Flag (30s) set ? | End of current block ? (loop back) | **No** |

## Facts the diagram must respect

- **Block toggle is top-of-loop**: `block_remaining == 0?` is checked before every
  batch. Yes → flip fresh/reused **and** reset `block_remaining = 100`.
- **Stop ends the run**: the 30s deadline sets the `stop` flag in the runner
  (`workload.rs:248`); the generator breaks — it does **not** toggle a block and continue.
- **Fresh fallback**: when `fresh_keys` is exhausted (every row id used once), fresh
  blocks sample from `used_keys` like reused blocks.
- **Decrement**: `n = min(batch, block_remaining)` — 1 per request with the default
  `batch=1`; a batch never mixes fresh and reused keys.
- Initial state: `is_fresh_block = true`, `block_remaining = 100`.
