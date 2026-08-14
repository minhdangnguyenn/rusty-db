#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"
SINCE="${3:-1 hour ago}"

echo "=== Checking for raft panics on $PREFIX cluster ==="
for i in 1 2 3 4 5; do
  echo "  $PREFIX-node-$i:"
  gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
    --command "sudo journalctl -u toydb --since '$SINCE' 2>/dev/null | grep -i panic || echo '    no panics'" \
    | sed 's/^/    /'
done
