# Plot Scripts

## Directory Structure

```
plot/
├── config.py                   # Shared config (colors, CI helpers using t-distribution, legend)
├── throughput.py               # Single-CSV throughput line chart
├── latency.py                  # Single-CSV latency bar chart
├── cache-hit-rate.py           # Cache hit/miss rate over time
├── interval-throughput.py      # CI throughput from a directory of runs
├── interval-latency.py         # CI latency bar chart from a directory
├── compare-throughput-s.py     # Stacked throughput subplots (2 dirs)
├── compute-mean.py             # Average multiple runs into avg.csv
├── compute-exp3-avg.py         # Aggregate all exp3 levels into avg-exp3.csv
├── throughput-latency.sh       # Wrapper: throughput + hit-rate + latency
├── exp1/
│   ├── compare-throughput.py   # CI throughput, 2 directories
│   ├── compare-latency.py      # CI latency bar + diff, 2 directories
│   ├── compare-hitrate-size.py # Hit/miss ratio between 2 configs
│   ├── cache-comparison-all.py # 4 configs on one chart
│   ├── compare-throughput.sh   # Legacy runner
│   └── compare-latency.sh      # Legacy runner
├── exp2/
│   ├── compare-throughput.py   # Throughput, 2 avg CSVs (FIFO vs LRU)
│   ├── compare-latency.py      # Latency, 2 avg CSVs
│   ├── compare-hit-miss.py     # Hit/miss ratio, 2 avg CSVs (same as compare-hitmiss.py)
│   ├── compare-hitmiss.py      # Identical to compare-hit-miss.py
│   ├── compare.sh              # Runner: avg -> 4 chart types
│   └── regen-exp2-zipf.sh      # Legacy regen script
└── exp3/
    ├── compare-throughput-exp3.py  # Throughput over time for all 5 CC levels
    ├── compare-s-vs-l-exp3.py      # Small vs large error bar
    ├── mmm-throughput.py           # M/M/m throughput prediction
    └── mmm-responsetime.py         # M/M/m response time prediction
```

## Data Conventions

CSV data is organized as:

```
csv/cloud/exp1/{cache,no-cache}/{size}/{dist}/{id}/
csv/cloud/exp2/fifo/{size}/{dist}/{id}/       (LRU data comes from csv/cloud/exp1/cache/)
csv/cloud/exp3/{c4,c8,c16,c32,c64}/{size}/{dist}/{id}/
csv/cloud/exp3-nocache/{dist}/{label}/{size}/{id}/
```

- `{size}`: `l` (10000 rows) or `s` (1000 rows)
- `{dist}`: `zipf` or `uniform`
- `{id}`: run number (1-5)
- `{label}`: concurrency level (c1, c4, c8, c16, c32, c64)

Chart output goes to `charts/cloud/exp{1,2,3}/`.

## Color Convention

| Data | Color |
|------|-------|
| Cache / exp1 | `#2196F3` (blue) |
| No-cache | `#F44336` (red) |
| FIFO / exp2 | `#F44336` (red) |
| LRU / exp2 (from exp1/cache) | `#2196F3` (blue) |
| `interval-throughput.py` auto-detects: no-cache in path -> red, else -> blue |

## Script Reference

### Shared Scripts

#### `throughput.py`
Plot a single CSV as a throughput-vs-time line chart.

```
usage: throughput.py csv [--label LABEL] [--color COLOR] [--marker MARKER] [-o OUTPUT]
```

#### `latency.py`
Plot the last row's latency percentiles (p50, p90, p99, max) as a bar chart.

```
usage: latency.py csv [-o OUTPUT]
```

#### `cache-hit-rate.py`
Plot hit and miss ratio over time from a single CSV.

```
usage: cache-hit-rate.py csv [--label LABEL] [-o OUTPUT]
```

#### `interval-throughput.py`
Compute mean + 95% CI across multiple runs in a directory and plot throughput.

```
usage: interval-throughput.py [dir] [--color COLOR] [-o OUTPUT]
```

Auto-detects `no-cache` in the path to pick red; otherwise defaults to blue.

#### `interval-latency.py`
Compute mean + 95% CI for percentiles across runs and plot a bar chart.

```
usage: interval-latency.py [dir] [-o OUTPUT]
```

#### `compare-throughput-s.py`
Two stacked subplots (own y-scale each), computes CI from directories.

```
usage: compare-throughput-s.py dir1 dir2 [--label1 L1] [--label2 L2]
                                        [--color1 C1] [--color2 C2] [-o OUTPUT]
```

#### `compute-mean.py`
Align runs by `time_s` and produce `avg.csv` with mean + 95% CI per column.

```
usage: compute-mean.py dir [-o OUTPUT]
```

#### `compute-exp3-avg.py`
Aggregate all exp3 concurrency levels into `csv/cloud/exp3/{size}/{dist}/avg-exp3.csv`.
No arguments; hardcodes the level list and size/dist combos.
Note: reads c16 data from `exp1/cache/` instead of `exp3/c16/`.

#### `throughput-latency.sh`
Wrapper that runs `throughput.py` + `cache-hit-rate.py` + `latency.py` on one CSV.

```
usage: throughput-latency.sh <csv> [label]
```

### Exp1 -- Cache vs No-cache

#### `compare-throughput.py`
Compute CI from two directories and overlay throughput lines.

```
usage: compare-throughput.py dir1 dir2 [--label1 L1] [--label2 L2]
                                       [--color1 C1] [--color2 C2] [-o OUTPUT]
```

Default: dir1 = cache (blue), dir2 = no-cache (red).

#### `compare-latency.py`
Compute CI latency from two directories and plot side-by-side bars + diff.

```
usage: compare-latency.py dir1 dir2 [--label1 L1] [--label2 L2]
                                     [--color1 C1] [--color2 C2] [-o OUTPUT]
```

#### `compare-hitrate-size.py`
Compare cache hit or miss ratio between two configurations (reads `avg.csv` from each directory).

```
usage: compare-hitrate-size.py dir1 dir2
       [--metric {hit,miss}] [--label1 L1] [--label2 L2]
       [--color1 C1] [--color2 C2] [-o OUTPUT]
```

Used for small vs large dataset comparison, or uniform vs zipf for the same size.
Default output path: `charts/{label1}-{label2}-{metric}.png` (always pass `-o` to place in `charts/cloud/exp1/`).

#### `cache-comparison-all.py`
Plot all 4 Exp1 configurations (cache uniform, cache zipf, no-cache uniform, no-cache zipf) as a single throughput-over-time chart with CI bands.

```
usage: cache-comparison-all.py
```

Hardcoded paths -- reads from `csv/cloud/exp1/{cache,no-cache}/l/{uniform,zipf}/`.
Outputs to `charts/cloud/exp1/throughput-all-large.png`.

### Exp2 -- FIFO vs LRU

Inputs are avg CSV files (produced by `compute-mean.py`). LRU data comes from
`csv/cloud/exp1/cache/`, not from `csv/cloud/exp2/`.

#### `compare-throughput.py`

```
usage: compare-throughput.py csv1 csv2 [-o OUTPUT]
```

FIFO = red `#F44336` square, LRU = blue `#2196F3` triangle.

#### `compare-latency.py`

```
usage: compare-latency.py csv1 csv2 [-o OUTPUT]
```

Default output: `charts/compare-latency-{labels}.png` (always pass `-o` to place correctly).

#### `compare-hit-miss.py`
Compare hit or miss ratio with 95% CI bands.

```
usage: compare-hit-miss.py csv1 csv2 --metric {hit,miss} [--label1 L1] [--label2 L2]
                                                         [-o OUTPUT]
```

#### `compare.sh`
Full runner:
1. Generate `avg.csv` for FIFO (`exp2/fifo/`) and LRU (`exp1/cache/`) data
2. Plot throughput, latency, hit-ratio, miss-ratio for all size/dist combos

```
bash plot/exp2/compare.sh
```

Outputs go to:
- `charts/cloud/exp2/compare/{size}/throughput/{dist}.png`
- `charts/cloud/exp2/compare/{size}/latency/{dist}.png`
- `charts/cloud/exp2/compare/{size}/hit-miss-ratio/hit-ratio-{size}-{dist}.png`
- `charts/cloud/exp2/compare/{size}/hit-miss-ratio/miss-ratio-{size}-{dist}.png`

### Exp3 -- Concurrency Scaling

Exp3 varies concurrency level K (4, 8, 16, 32, 64) to study how throughput and
response time scale. The M/M/m model uses the closed-form queueing formulas
from lecture 5a. The service rate mu is estimated from a separate no-cache
run at K=1 (from `csv/cloud/exp3-nocache/`). Predicted throughput is computed
by solving the closed-system fixed-point equation lambda = K / E[r](lambda)
via binary search.

#### `compare-throughput-exp3.py`
Plot 5 throughput-over-time lines (c4, c8, c16, c32, c64) for all 4 combos
(size x dist). Each line shows the mean across 5 runs.

| Level | Color | Marker |
|-------|-------|--------|
| c4 | `#e41a1c` red | circle |
| c8 | `#377eb8` blue | square |
| c16 | `#4daf4a` green | triangle |
| c32 | `#984ea3` purple | diamond |
| c64 | `#ff7f00` orange | triangle-down |

```
usage: compare-throughput-exp3.py
```

Outputs to `charts/cloud/exp3/{size}/{dist}/compare-throughput-ci.png`.

#### `compare-s-vs-l-exp3.py`
Error bar chart comparing small (s, 1000 rows) vs large (l, 10000 rows)
throughput across CC levels.

```
usage: compare-s-vs-l-exp3.py
```

Outputs to `charts/cloud/exp3/throughput-s-vs-l/{dist}.png`.

#### `mmm-throughput.py`
Fit M/M/m model to throughput data. Reads the no-cache c1 data (from
`csv/cloud/exp3-nocache/`) to estimate mu, then computes closed M/M/m
predictions for each concurrency level. Overlays measured (with-cache)
throughput with 95% CI and the predicted line on the same chart.

```
usage: python mmm-throughput.py
```

Outputs 4 files: `charts/cloud/exp3/mmm-throughput-{s,l}-{uniform,zipf}.png`.

#### `mmm-responsetime.py`
Same as mmm-throughput.py but for response time (ms). Response time is
derived from throughput via Little's law: E[r] = K / lambda.

```
usage: python mmm-responsetime.py
```

Outputs 4 files: `charts/cloud/exp3/mmm-responsetime-{s,l}-{uniform,zipf}.png`.

## Typical Workflows

```
# Exp1: compare cache vs no-cache for a single config
python plot/exp1/compare-throughput.py \
  csv/cloud/exp1/cache/l/zipf csv/cloud/exp1/no-cache/l/zipf \
  -o charts/cloud/exp1/l/zipf/compare-throughput.png

# Exp1: hit/miss ratio small vs large (uniform)
python plot/exp1/compare-hitrate-size.py \
  csv/cloud/exp1/cache/s/uniform csv/cloud/exp1/cache/l/uniform \
  --metric hit \
  -o charts/cloud/exp1/hitrate-size/uniform-hit.png

# Exp1: all 4 configs on one chart
python plot/exp1/cache-comparison-all.py

# Exp2: regenerate everything
bash plot/exp2/compare.sh

# Exp2: single config (compare FIFO vs LRU)
python plot/compute-mean.py csv/cloud/exp2/fifo/l/uniform
python plot/exp2/compare-throughput.py \
  csv/cloud/exp2/fifo/l/uniform/avg.csv \
  csv/cloud/exp1/cache/l/uniform/avg.csv \
  -o charts/cloud/exp2/compare/l/throughput/uniform.png

# Exp3: M/M/m model (all 4 combos)
python plot/exp3/mmm-throughput.py
python plot/exp3/mmm-responsetime.py

# Exp3: throughput over time
python plot/exp3/compare-throughput-exp3.py

# Exp3: small vs large comparison
python plot/exp3/compare-s-vs-l-exp3.py

# Single CSV quick view
bash plot/throughput-latency.sh csv/some-experiment.csv "My Label"
```
