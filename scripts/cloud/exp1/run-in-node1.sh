#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run-in-node1.sh [EXPERIMENT] [ID]
#   EXPERIMENT defaults to "exp1-cache-s-uniform"
#   ID         defaults to 1

ID=${2:-1}
EXP=${1:-exp1-cache-s-uniform}
ZONE=${ZONE:-europe-west3-c}
PREFIX=${PREFIX:-toydb}

# Queries GCP for each VM's internal VPC IP (networkIP, not natIP)
# and builds a comma-separated host string like 10.0.0.2:9601,10.0.0.3:9602,....

# Fetch internal IPs dynamically from GCP
INTERNAL_HOSTS=""
for i in 1 2 3 4 5; do
    ip=$(gcloud compute instances describe "$PREFIX-node-$i" --zone "$ZONE" \
        --format="value(networkInterfaces[0].networkIP)")
    [ -n "$INTERNAL_HOSTS" ] && INTERNAL_HOSTS+=","
    INTERNAL_HOSTS+="$ip:$((9600 + i))"
done

gcloud compute ssh "$PREFIX-node-1" --zone "$ZONE" -- \
  "cd /opt/toydb && ./target/release/workload -H '$INTERNAL_HOSTS' \
  --experiment $EXP --id $ID read --rows 1000 --cache"
