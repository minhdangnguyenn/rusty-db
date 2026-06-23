#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"

echo "=== Sanitizing $PREFIX cluster ==="
for i in 1 2 3 4 5; do
  echo "  Resetting $PREFIX-node-$i..."
  gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
    --command "sudo rm -f /opt/toydb/data/raft /opt/toydb/data/sql && sudo systemctl restart toydb"
done

echo "=== Waiting for nodes to become active ==="
for i in 1 2 3 4 5; do
  while true; do
    status=$(gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
      --command "systemctl is-active toydb" 2>/dev/null || echo "waiting")
    if [ "$status" = "active" ]; then
      echo "  ✅ $PREFIX-node-$i: active"
      break
    fi
    echo "  ⏳ $PREFIX-node-$i: $status, waiting..."
    sleep 3
  done
done

echo "=== Cluster ready ==="

# bash scripts/cloud-sanitize.sh               # default zone
# bash scripts/cloud-sanitize.sh us-central1-a  # custom zone
