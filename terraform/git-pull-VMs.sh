ZONE="${ZONE:-europe-west3-c}"
PREFIX="${PREFIX:-toydb}"

for i in 1 2 3 4 5; do
    echo "=== Syncing $PREFIX-node-$i ==="
    gcloud compute ssh "$PREFIX-node-$i" --zone "$ZONE" \
        --command "cd /opt/toydb && sudo git pull --rebase && sudo -H bash -lc 'cargo build --release --bin workload'"
done
