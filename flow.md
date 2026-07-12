# Workload Generation Flow

```mermaid
flowchart TD
    P0["Start"] --> P["Prepare Phase<br/><b>Bulk insert all keys</b><br/>1..rows into database<br/>(s: 1K, l: 10K)"]

    P --> S["Steady Phase (30s)<br/><b>Timer starts</b>"]

    S --> G["BlockGen starts</br>Shuffle all key IDs → fresh_keys</br>is_fresh_block = true, block_remaining = 100"]

    G --> CHECK{"fresh_idx<br/>&lt;<br/>fresh_keys.len() ?"}

    CHECK -- Yes --> FRESH_BLOCK{"block_remaining &gt; 0 ?"}

    FRESH_BLOCK -- Yes, batch=1 --> FRESH_READ["Take next key from fresh_keys<br/><b>INSERT into DB</b> (first access)<br/>key → used_keys pool"]

    FRESH_READ --> FRESH_DEC[block_remaining -= batch]

    FRESH_DEC --> FRESH_BLOCK

    FRESH_BLOCK -- No, block exhausted --> TOGGLE_F["is_fresh_block = false<br/>block_remaining = 100"]

    TOGGLE_F --> CHECK

    CHECK -- No --> USED_BLOCK{"is_fresh_block? &amp;<br/>block_remaining &gt; 0 ?"}

    USED_BLOCK -- Yes --> USED_READ["Sample key from used_keys<br/><b>SELECT from DB</b> (read)<br/>Zipf α=1.0 or uniform"]

    USED_READ --> USED_DEC[block_remaining -= batch]

    USED_DEC --> USED_BLOCK

    USED_BLOCK -- No, block exhausted --> TOGGLE_U["is_fresh_block = true<br/>block_remaining = 100"]

    TOGGLE_U --> CHECK

    CHECK -- Yes, but all blocks<br/>become pure reads --> LEGACY["<b>After all fresh keys consumed:</b><br/>Alternation continues,<br/>both block types read from used_keys<br/>Workload is 100% reads"]

    LEGACY --> USED_READ

    style P fill:#e3f2fd,stroke:#1565c0,color:#000
    style S fill:#fff3e0,stroke:#e65100,color:#000
    style G fill:#f3e5f5,stroke:#7b1fa2,color:#000
    style CHECK fill:#fff9c4,stroke:#f9a825,color:#000
    style FRESH_READ fill:#c8e6c9,stroke:#2e7d32,color:#000
    style USED_READ fill:#ffcdd2,stroke:#c62828,color:#000
    style LEGACY fill:#e8eaf6,stroke:#283593,color:#000
```

## Block Timeline Example (s = 1000 keys)

```
Block   1 [fresh]: keys 1..100     → INSERT (cache miss)
Block   2 [used]:  sample from 100  → SELECT
Block   3 [fresh]: keys 101..200   → INSERT (cache miss)
Block   4 [used]:  sample from 200  → SELECT
...
Block  19 [fresh]: keys 901..1000  → INSERT (cache miss)
Block  20 [used]:  sample from 1000 → SELECT
Block  21 [fresh]: fallback → sample from 1000 → SELECT
Block  22 [used]:  sample from 1000 → SELECT
...
```

- `block_size = 100`, `batch = 1` → mỗi block = 100 requests
- 1000 keys / 100 = 10 fresh blocks để consume hết fresh_keys
- Sau block 20, tất cả là pure reads (cả fresh lẫn used block đều sample từ used_keys)
- Mỗi request = 1 key (batch=1)

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--rows` | 1000 (s) / 10000 (l) | Total keys |
| `--block-size` | 100 | Requests per block |
| `--batch` | 1 | Keys per request |
| `--dist` | uniform / zipf | Sampling distribution |
| `--zipf-skew` | 1.0 | Zipf skew parameter |
| `--duration` | 30 | Benchmark duration (seconds) |
