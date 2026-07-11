#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"

echo "=== Stopping all $PREFIX VMs ==="
for i in 1 2 3 4 5; do
  echo "  Stopping $PREFIX-node-$i..."
done

gcloud compute instances stop "$PREFIX-node-1" "$PREFIX-node-2" "$PREFIX-node-3" "$PREFIX-node-4" "$PREFIX-node-5" \
  --zone "$ZONE"

echo "=== Done ==="
