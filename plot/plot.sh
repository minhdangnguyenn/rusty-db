#!/bin/bash
# generate throughput and latency charts from a data csv file
# usage: bash plot/plot-charts.sh <csv-file> [label]
#   csv-file: path to the data csv (e.g. csv/no-cache-read-s-uniform-3.csv)
#   label:    optional legend label (default: auto-derived)
#
# examples:
#   bash plot/plot-charts.sh csv/no-cache-read-s-uniform-3.csv
#   bash plot/plot-charts.sh csv/no-cache-read-s-uniform-3.csv "no-cache"
#   bash plot/plot-charts.sh csv/cache-read-s-uniform-1.csv csv/no-cache-read-s-uniform-3.csv --labels cache no-cache

PYTHON=/tmp/opencode/plot-env/bin/python3
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

$PYTHON "$SCRIPT_DIR/plot-throughput.py" "$@"
$PYTHON "$SCRIPT_DIR/plot-latency.py" "$@"
echo "charts saved to charts/"
