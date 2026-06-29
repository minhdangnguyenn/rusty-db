#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python3"

find_csvs() {
    find csv -path '*/exp3/*' -name '*.csv' ! -name '*summary*'
}

count=0
skipped=0
while IFS= read -r csv; do
    rel="${csv#csv/}"
    rows=$(wc -l < "$csv")
    if [ "$rows" -le 1 ]; then
        echo "[SKIP] $rel (${rows} line(s))"
        skipped=$((skipped + 1))
        continue
    fi
    base="${rel%.csv}"
    dir="charts/$(dirname "$rel")"
    mkdir -p "$dir"

    echo "[$((count + 1))] $rel (${rows} rows)"

    "$PYTHON" "$SCRIPT_DIR/plot-throughput.py" "$csv" -o "$dir/$(basename "$base")-throughput.png"
    "$PYTHON" "$SCRIPT_DIR/plot-latency.py" "$csv" -o "$dir/$(basename "$base")-latency.png"
    "$PYTHON" "$SCRIPT_DIR/plot-cache-hit-rate.py" "$csv" -o "$dir/$(basename "$base")-cache-hit-rate.png"

    count=$((count + 1))
done < <(find_csvs)

echo "Done — $count CSVs plotted, $skipped skipped ($((count * 3)) charts generated)."

echo "Done — $count CSVs processed, $((count * 3)) charts generated."
