#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../.."

PYTHON="plot/.venv/bin/python3"

echo "=== Step 1: Generate avg CSVs ==="

for dist in zipf uniform; do
  for size in l s; do
    dir="csv/cloud/exp2/fifo/${size}/${dist}"
    if [ -d "$dir" ]; then
      echo "  FIFO ${size}/${dist}..."
      $PYTHON plot/compute-mean.py "$dir" -o "${dir}/avg.csv"
    fi
  done
done

for dist in zipf uniform; do
  for size in l s; do
    dir="csv/cloud/exp1/cache/${dist}/${size}"
    if [ -d "$dir" ]; then
      echo "  LRU (cache) ${size}/${dist}..."
      $PYTHON plot/compute-mean.py "$dir" -o "${dir}/avg.csv"
    fi
  done
done

echo "=== Step 2: Plot compare FIFO vs LRU ==="

for dist in zipf uniform; do
  for size in l s; do
    echo "--- ${size}/${dist} ---"
    fifo_csv="csv/cloud/exp2/fifo/${size}/${dist}/avg.csv"
    lru_csv="csv/cloud/exp1/cache/${dist}/${size}/avg.csv"

    if [ ! -f "$fifo_csv" ] || [ ! -f "$lru_csv" ]; then
      echo "  Skip: missing avg CSVs for ${size}/${dist}"
      continue
    fi

    for dir in throughput latency hit-miss-ratio; do
      mkdir -p "charts/cloud/exp2/compare/${size}/${dir}"
    done

    $PYTHON plot/exp2/compare-throughput.py \
      "$fifo_csv" "$lru_csv" \
      -o "charts/cloud/exp2/compare/${size}/throughput/${dist}.png"

    $PYTHON plot/exp2/compare-latency.py \
      "$fifo_csv" "$lru_csv" \
      -o "charts/cloud/exp2/compare/${size}/latency/${dist}.png"

    $PYTHON plot/exp2/compare-hit-ratio.py \
      "$fifo_csv" "$lru_csv" \
      -o "charts/cloud/exp2/compare/${size}/hit-miss-ratio/hit-ratio-${size}-${dist}.png"

    $PYTHON plot/exp2/compare-miss-ratio.py \
      "$fifo_csv" "$lru_csv" \
      -o "charts/cloud/exp2/compare/${size}/hit-miss-ratio/miss-ratio-${size}-${dist}.png"
  done
done

echo "=== All done ==="
