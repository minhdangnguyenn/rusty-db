#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"
DURATION="${3:-3}"
CONCURRENCY="${4:-4}"
ROWS="${5:-1000}"
SEED="${6:-123}"

echo "=== Building TOYDB_HOSTS from internal IPs ==="
HOSTS=""
for i in 1 2 3 4 5; do
  ip=$(gcloud compute instances describe "$PREFIX-node-$i" --zone "$ZONE" \
    --format="value(networkInterfaces[0].networkIP)")
  [ -n "$HOSTS" ] && HOSTS+=","
  HOSTS+="$ip:$((9600 + i))"
done
echo "  TOYDB_HOSTS=$HOSTS"

echo "=== Running sanity workload on $PREFIX-node-1 ==="
gcloud compute ssh "$PREFIX-node-1" --zone "$ZONE" --command "
  export TOYDB_HOSTS='$HOSTS'
  cd /opt/toydb
  ./target/release/workload -H '$HOSTS' \
    --experiment verify --id 1 \
    --out-dir /tmp \
    --duration $DURATION --timeout 10 \
    read --rows $ROWS
  echo \"  exit code: \$?\"
  tail -1 /tmp/verify-1-summary.csv 2>/dev/null || true
"
