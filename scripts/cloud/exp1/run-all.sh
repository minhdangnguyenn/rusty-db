#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

for kind in cache no-cache; do
  for size in s l; do
    for dist in uniform zipf; do
      echo "=== Running exp1 $kind $size $dist (IDs 1-5) ==="
      for id in 1 2 3 4 5; do
        bash "$BASE_DIR/$kind/$size/$dist.sh" "$id"
      done
    done
  done
done

echo "=== All exp1 experiments done ==="
