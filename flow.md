# Workload Generation Flow

```mermaid
flowchart TB
    PREPARE["Prepare Phase<br/>Bulk insert all keys"]
    STEADY["Steady Phase (30s)<br/>Timer starts"]
    NEXT["BlockGen.next()<br/>called per request"]
    BLOCK_END{"block_remaining<br/>== 0 ?"}
    TOGGLE["Toggle is_fresh_block<br/>Reset block_remaining = 100"]
    FRESH{"is_fresh_block<br/>& fresh_keys<br/>remaining ?"}
    FRESH_KEY["Take next key from fresh_keys<br/>First access → cache miss"]
    USED["Sample key from used_keys<br/>Read from DB (Zipf/uniform)"]
    DEC["block_remaining -= 1<br/>(batch=1)"]

    PREPARE --> STEADY
    STEADY --> NEXT
    NEXT --> BLOCK_END
    BLOCK_END -- Yes --> TOGGLE
    BLOCK_END -- No --> FRESH
    TOGGLE --> FRESH
    FRESH -- Yes --> FRESH_KEY
    FRESH -- No --> USED
    FRESH_KEY --> DEC
    USED --> DEC
    DEC --> NEXT
```

## Timeline (s = 1,000 keys, block_size = 100)

```
Block   1 (fresh): keys   1..100   → first access (cache miss)
Block   2 (used):  from   100 keys → read
Block   3 (fresh): keys 101..200   → first access (cache miss)
Block   4 (used):  from   200 keys → read
...
Block  19 (fresh): keys 901..1000  → first access (cache miss)
Block  20 (used):  from  1000 keys → read
Block  21 (fresh): fallback (no fresh_keys left), sample from used_keys
Block  22 (used):  sample from used_keys
...pure reads for the rest of the 30s
```

## Key Parameters

| Parameter | s | l |
|-----------|---|---|
| Total keys | 1,000 | 10,000 |
| Block size | 100 | 100 |
| Fresh → used toggle | every 100 requests | every 100 requests |
| Fresh keys exhausted | after block 20 | after block 200 |
| After exhaustion | pure reads (Zipf/uniform) | pure reads |

## Notes

- Data is fully inserted during **Prepare** — fresh keys are not inserted into the DB during the benchmark, they are simply read for the first time, causing a cache miss.
- `BlockGen` is an **infinite iterator** — it never terminates. The benchmark stops after 30 seconds (`--duration 30`).
