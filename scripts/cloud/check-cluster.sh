#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"
MINUTES="${3:-5}"

echo "=== Cluster status ==="
for i in 1 2 3 4 5; do
  echo "  $PREFIX-node-$i:"
  gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" --command "
    echo -n '    service: '; systemctl is-active toydb
    echo -n '    proc start: '; ps -o lstart= -p \$(pgrep -f 'target/release/toydb' | head -1) 2>/dev/null
    echo -n '    panics (${MINUTES}m): '; sudo journalctl -u toydb --since '${MINUTES} minutes ago' 2>/dev/null | grep -ci panic || true
  " | sed 's/^/    /'
done
