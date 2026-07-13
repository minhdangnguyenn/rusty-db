# Plot Scripts

## Directory Structure

```
plot/
├── config.py                   # Shared config (colors, CI helpers, legend)
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
│   ├── compare-hitrate-size.py # Hit/miss ratio between 2 configs (s vs l, uniform vs zipf)
│   ├── cache-comparison-all.py # 4 configs (cache/no-cache × uniform/zipf) on one chart
│   ├── compare-throughput.sh   # Legacy runner
│   └── compare-latency.sh      # Legacy runner
├── exp2/
│   ├── compare-throughput.py   # Throughput, 2 avg CSVs (FIFO vs LRU)
│   ├── compare-latency.py      # Latency, 2 avg CSVs
│   ├── compare-metric.py       # Hit/miss ratio, 2 avg CSVs
│   ├── compare-hit-miss.py     # Legacy (identical to compare-hitmiss.py)
│   ├── compare-hitmiss.py      # Legacy
│   ├── compare.sh              # Runner: avg → 4 chart types
│   └── regen-exp2-zipf.sh      # Legacy regen script
└── exp3/
    ├── compare-throughput-exp3.py  # 5 CC levels, 4 combos
    ├── compare-s-vs-l-exp3.py      # Small vs large error bar
    └── mmm-model.py                # M/M/m model fit
```

## Data Conventions

CSV data is organized as:

```
csv/cloud/exp1/{cache,no-cache}/{size}/{dist}/{id}/
csv/cloud/exp2/{fifo,lru}/{size}/{dist}/{id}/
csv/cloud/exp3/{c4,c8,c16,c32,c64}/{size}/{dist}/{id}/
```

- `{size}`: `l` (10000 rows) or `s` (1000 rows)
- `{dist}`: `zipf` or `uniform`
- `{id}`: run number (1–5)

Chart output mirrors the data structure under `charts/cloud/`.

## Color Convention

| Data | Color |
|------|-------|
| Cache / `exp1_color` | `#2196F3` (blue) |
| No-cache / `exp2_color` | `#F44336` (red) |
| `interval-throughput.py` auto-detects: no-cache path → red, else → blue |

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

#### `throughput-latency.sh`
Wrapper that runs `throughput.py` + `cache-hit-rate.py` + `latency.py` on one CSV.

```
usage: throughput-latency.sh <csv> [label]
```

### Exp1 — Cache vs No-cache

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

#### `cache-comparison-all.py`
Plot all 4 Exp1 configurations (cache uniform, cache zipf, no-cache uniform, no-cache zipf) as a single throughput-over-time chart with CI bands.

```
usage: cache-comparison-all.py
```

Hardcoded paths — reads from `csv/cloud/exp1/{cache,no-cache}/l/{uniform,zipf}/`.
Outputs to `charts/cloud/exp1/throughput-all-large.png`.

### Exp2 — FIFO vs LRU

Inputs are avg CSV files (produced by `compute-mean.py`).

#### `compare-throughput.py`

```
usage: compare-throughput.py csv1 csv2 [-o OUTPUT]
```

FIFO = red `#F44336` square, LRU = blue `#2196F3` triangle.

#### `compare-latency.py`

```
usage: compare-latency.py csv1 csv2 [-o OUTPUT]
```

#### `compare-metric.py`
Compare hit or miss ratio with 95 % CI bands.

```
usage: compare-metric.py csv1 csv2 --metric {hit,miss} [--label1 L1] [--label2 L2]
                                                        [-o OUTPUT]
```

#### `compare.sh`
Full runner:
1. Generate `avg.csv` for FIFO and LRU (cache) data
2. Plot throughput, latency, hit-ratio, miss-ratio for all size/dist combos

```
bash plot/exp2/compare.sh
```

Outputs go to `charts/cloud/exp2/compare/{size}/{throughput,latency,hit-miss-ratio}/`.

### Exp3 — Concurrency Scaling

Scripts are fully self-contained: they read raw CSV directories directly (no avg CSV needed).

#### `compare-throughput-exp3.py`
Plot 5 throughput lines (c4, c8, c16, c32, c64) per combo. x-axis = 0–30 s.

| Level | Color | Marker |
|-------|-------|--------|
| c4 | `#e41a1c` red | ○ circle |
| c8 | `#377eb8` blue | □ square |
| c16 | `#4daf4a` green | △ triangle |
| c32 | `#984ea3` purple | ◇ diamond |
| c64 | `#ff7f00` orange | ▽ triangle-down |

```
usage: compare-throughput-exp3.py
```

Outputs to `charts/cloud/exp3/{size}/{dist}/compare-throughput-ci.png`.

#### `compare-s-vs-l-exp3.py`
Error bar chart comparing small (s, 1000 rows) vs large (l, 10000 rows) throughput across CC levels.

```
usage: compare-s-vs-l-exp3.py
```

Outputs to `charts/cloud/exp3/throughput-s-vs-l/{dist}.png`.

#### `mmm-model.py`
Fit M/M/m model to measured throughput data.

```
usage: mmm-model.py --mode {throughput,response-time}
```

Plots measured ± 95 % CI alongside the M/M/m ideal line.
Outputs to `charts/cloud/exp3/{size}/{dist}/mmm-{mode}.png`.

## Typical Workflows

```bash
# Exp1: compare cache vs no-cache for a single config
python plot/exp1/compare-throughput.py \
  csv/cloud/exp1/cache/l/zipf csv/cloud/exp1/no-cache/l/zipf \
  -o charts/cloud/exp1/l/zipf/compare-throughput.png

# Exp1: hit/miss ratio small vs large (uniform)
python plot/exp1/compare-hitrate-size.py \
  csv/cloud/exp1/cache/s/uniform csv/cloud/exp1/cache/l/uniform \
  --metric hit

# Exp1: hit/miss ratio uniform vs zipf (small)
python plot/exp1/compare-hitrate-size.py \
  csv/cloud/exp1/cache/s/uniform csv/cloud/exp1/cache/s/zipf \
  --metric hit --label1 "Uniform" --label2 "Zipf"

# Exp1: all 4 configs on one chart (cache/no-cache × uniform/zipf)
python plot/exp1/cache-comparison-all.py

# Exp2: regenerate everything
bash plot/exp2/compare.sh

# Exp2: single config
plot/.venv/bin/python plot/compute-mean.py csv/cloud/exp2/fifo/l/uniform
plot/.venv/bin/python plot/compute-mean.py csv/cloud/exp1/cache/l/uniform
plot/.venv/bin/python plot/exp2/compare-throughput.py \
  csv/cloud/exp2/fifo/l/uniform/avg.csv csv/cloud/exp1/cache/l/uniform/avg.csv \
  -o charts/cloud/exp2/compare/l/throughput/uniform.png

# Exp3: all plots
plot/.venv/bin/python plot/exp3/compare-throughput-exp3.py
plot/.venv/bin/python plot/exp3/compare-s-vs-l-exp3.py
plot/.venv/bin/python plot/exp3/mmm-model.py --mode throughput
plot/.venv/bin/python plot/exp3/mmm-model.py --mode response-time

# Single CSV quick view
bash plot/throughput-latency.sh csv/some-experiment.csv "My Label"
```
