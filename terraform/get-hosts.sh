echo "=== Getting external IPs ==="
HOSTS=""
ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"
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
