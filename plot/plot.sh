#!/bin/bash
# generate throughput and latency charts from a data csv file
# usage: bash plot/plot.sh <csv-file> [label]
#   csv-file: path to the data csv (e.g. csv/no-cache-read-s-uniform-3.csv)
#   label:    optional legend label (default: auto-derived)
#
# examples:
#   bash plot/plot.sh csv/no-cache-read-s-uniform-3.csv
#   bash plot/plot.sh csv/no-cache-read-s-uniform-3.csv "no-cache"
#   bash plot/plot.sh csv/cache.csv csv/no-cache.csv --labels cache no-cache

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON="$SCRIPT_DIR/.venv/bin/python3"

case "$1" in
  --overlay)
    shift
    $PYTHON "$SCRIPT_DIR/plot-overlay.py" "$@"
    ;;
  --compare)
    shift
    $PYTHON "$SCRIPT_DIR/plot-compare.py" "$@"
    ;;
  *)
    if [ $# -gt 2 ]; then
      $PYTHON "$SCRIPT_DIR/plot-compare.py" "$@"
    elif [ $# -eq 2 ]; then
      $PYTHON "$SCRIPT_DIR/plot-throughput.py" "$1" --labels "$2"
      $PYTHON "$SCRIPT_DIR/plot-latency.py" "$1"
    else
      $PYTHON "$SCRIPT_DIR/plot-throughput.py" "$@"
      $PYTHON "$SCRIPT_DIR/plot-latency.py" "$@"
    fi
    ;;
esac
echo "charts saved to charts/"

#
# usage
# --------
# 1. Single experiment, auto-label:
#    bash plot/plot.sh csv/no-cache-read-s-uniform-3.csv
#
# 2. Single experiment with custom label:
#    bash plot/plot.sh csv/no-cache-read-s-uniform-3.csv "no-cache"
#
# 3. Compare multiple experiments (bar charts, requires summary CSVs):
#    bash plot/plot.sh csv/a-summary.csv csv/b-summary.csv --labels "A" "B"
#    # or shorthand for 3+ files:
#    bash plot/plot.sh csv/a-summary.csv csv/b-summary.csv csv/c-summary.csv --labels A B C
#
# 4. Overlay two experiments on dual y-axes:
#    bash plot/plot.sh --overlay csv/no-cache.csv csv/cache.csv --labels "no-cache" "cache"
#
# 5. Compare mode explicitly (same as #3):
#    bash plot/plot.sh --compare csv/a-summary.csv csv/b-summary.csv --labels "A" "B"
#
# Output files are saved under charts/ directory.
