#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"

echo "=== Killing stuck workload on $PREFIX-node-1 ==="
gcloud compute ssh "$PREFIX-node-1" --zone "$ZONE" --command "
  sudo pkill -f 'target/release/workload' || true
  sleep 1
  if pgrep -f 'target/release/workload' >/dev/null; then
    echo '  still running'
    exit 1
  fi
  echo '  clean'
"
