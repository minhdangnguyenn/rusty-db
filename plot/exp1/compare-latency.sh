#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON="$(dirname "$SCRIPT_DIR")/.venv/bin/python3"

$PYTHON "$SCRIPT_DIR/compare-latency.py" "$1" "$2"
echo "compare latency chart saved to charts/"
