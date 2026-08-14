#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"

echo "=== Sanitizing $PREFIX cluster ==="

# Stop all nodes first, then wipe, then start. Wiping one node at a time while
# the cluster is live leaves nodes with mixed logs (some empty, some holding
# committed entries from the previous epoch), which can panic raft with
# "spliced entries below commit index" (src/raft/log.rs:328).
echo "  Stopping toydb on all nodes..."
for i in 1 2 3 4 5; do
  gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
    --command "sudo systemctl stop toydb"
done

echo "  Wiping raft + sql data on all nodes..."
for i in 1 2 3 4 5; do
  gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
    --command "sudo rm -f /opt/toydb/data/raft /opt/toydb/data/sql"
done

echo "  Starting toydb on all nodes..."
for i in 1 2 3 4 5; do
  gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
    --command "sudo systemctl start toydb"
done

echo "=== Waiting for nodes to become active ==="
for i in 1 2 3 4 5; do
  while true; do
    status=$(gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
      --command "systemctl is-active toydb" 2>/dev/null || echo "waiting")
    if [ "$status" = "active" ]; then
      echo "  $PREFIX-node-$i: active"
      break
    fi
    echo " $PREFIX-node-$i: $status, waiting..."
    sleep 3
  done
done

echo "=== Cluster ready ==="
