#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"

HOSTS=""
for i in 1 2 3 4 5; do
  ip=$(gcloud compute instances describe "$PREFIX-node-$i" --zone "$ZONE" \
    --format="value(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null)
  [ -n "$ip" ] || { echo "Error: could not get IP for $PREFIX-node-$i" >&2; exit 1; }
  [ -n "$HOSTS" ] && HOSTS+=","
  HOSTS+="$ip:$((9600 + i))"
done

echo "export TOYDB_HOSTS=\"$HOSTS\""
