#!/usr/bin/env bash
set -euo pipefail

ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"
TIMEOUT=300
INTERVAL=5

echo "=== Waiting for all $PREFIX nodes to be ready ==="
end=$((SECONDS + TIMEOUT))
nodes=("$PREFIX-node-1" "$PREFIX-node-2" "$PREFIX-node-3" "$PREFIX-node-4" "$PREFIX-node-5")

for node in "${nodes[@]}"; do
    ready=false
    while [ $SECONDS -lt $end ]; do
        status=$(gcloud compute ssh "$node" --zone "$ZONE" \
            --command "systemctl is-active toydb" 2>/dev/null || echo "waiting")
        if [ "$status" = "active" ]; then
            echo "  ✅ $node: active"
            ready=true
            break
        fi
        echo "  ⏳ $node: $status, waiting ${INTERVAL}s..."
        sleep "$INTERVAL"
    done
    if [ "$ready" = false ]; then
        echo "  ❌ $node: timeout after ${TIMEOUT}s"
        exit 1
    fi
done

echo ""
echo "=== Getting external IPs ==="
HOSTS=""
for i in 1 2 3 4 5; do
    ip=$(gcloud compute instances describe "$PREFIX-node-$i" --zone "$ZONE" \
        --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
    [ -n "$HOSTS" ] && HOSTS+=","
    HOSTS+="$ip:$((9600 + i))"
    echo "  $PREFIX-node-$i: $ip"
done

echo ""
echo "=== Export TOYDB_HOSTS ==="
echo ""
echo "  export TOYDB_HOSTS=\"$HOSTS\""
echo ""
echo "=== Quick test ==="
./target/release/workload -H "$HOSTS" --experiment test-connect read --rows 1 -n 1
