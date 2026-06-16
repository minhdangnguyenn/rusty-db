#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python3"
CSV=$1
LABEL=${2:-}
if [ -z "$CSV" ]; then
    echo "Usage: $0 <csv-file> [label]"
    exit 1
fi
if [ -n "$LABEL" ]; then
    $PYTHON "$SCRIPT_DIR/plot-throughput.py" "$CSV" --labels "$LABEL"
    $PYTHON "$SCRIPT_DIR/plot-latency.py" "$CSV" --labels "$LABEL"
else
    $PYTHON "$SCRIPT_DIR/plot-throughput.py" "$CSV"
    $PYTHON "$SCRIPT_DIR/plot-latency.py" "$CSV"
fi

# sample usage
# bash plot/plot-throughput-latency.sh csv/no-cache-read-s-uniform-3.csv
# bash plot/plot-throughput-latency.sh csv/no-cache-read-s-uniform-3.csv "Small Uniform"
