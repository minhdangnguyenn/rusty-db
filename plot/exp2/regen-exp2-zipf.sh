#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHON="plot/.venv/bin/python"

echo "=== Generate avg CSVs ==="

for size in l s; do
  dir="csv/cloud/exp2/fifo/${size}/zipf"
  if [ -d "$dir" ]; then
    echo "  FIFO ${size}/zipf..."
    $PYTHON plot/compute-mean.py "$dir" -o "${dir}/avg.csv"
  fi
done

for size in l s; do
  dir="csv/cloud/exp1/cache/zipf/${size}"
  if [ -d "$dir" ]; then
    echo "  LRU (cache) ${size}/zipf..."
    $PYTHON plot/compute-mean.py "$dir" -o "${dir}/avg.csv"
  fi
done

echo "=== Plot compare FIFO vs LRU ==="

for size in l s; do
  echo "--- ${size}/zipf ---"
  fifo_csv="csv/cloud/exp2/fifo/${size}/zipf/avg.csv"
  lru_csv="csv/cloud/exp1/cache/zipf/${size}/avg.csv"

  if [ ! -f "$fifo_csv" ] || [ ! -f "$lru_csv" ]; then
    echo "  Skip: missing avg CSVs for ${size}"
    continue
  fi

  for dir in throughput latency hit-miss-ratio; do
    mkdir -p "charts/cloud/exp2/compare/${size}/${dir}"
  done

  $PYTHON plot/exp2/compare-throughput.py \
    "$fifo_csv" "$lru_csv" \
    -o "charts/cloud/exp2/compare/${size}/throughput/zipf.png"

  $PYTHON plot/exp2/compare-latency.py \
    "$fifo_csv" "$lru_csv" \
    -o "charts/cloud/exp2/compare/${size}/latency/zipf.png"

  $PYTHON plot/exp2/compare-metric.py \
    "$fifo_csv" "$lru_csv" \
    --metric hit \
    -o "charts/cloud/exp2/compare/${size}/hit-miss-ratio/hit-ratio-${size}-zipf.png"

  $PYTHON plot/exp2/compare-metric.py \
    "$fifo_csv" "$lru_csv" \
    --metric miss \
    -o "charts/cloud/exp2/compare/${size}/hit-miss-ratio/miss-ratio-${size}-zipf.png"
done

echo "=== All done ==="
