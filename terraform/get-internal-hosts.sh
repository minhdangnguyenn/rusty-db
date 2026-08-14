# export TOYDB_HOSTS="10.0.0.2:9601,10.0.0.3:9602,10.0.0.5:9603,10.0.0.6:9604,10.0.0.4:9605"

echo "=== Getting internal IPs ==="
HOSTS=""
ZONE="${1:-europe-west3-c}"
PREFIX="${2:-toydb}"
for i in 1 2 3 4 5; do
    ip=$(gcloud compute instances describe "$PREFIX-node-$i" --zone "$ZONE" \
        --format="value(networkInterfaces[0].networkIP)")
    [ -n "$HOSTS" ] && HOSTS+=","
    HOSTS+="$ip:$((9600 + i))"
    echo "  $PREFIX-node-$i: $ip:$((9600 + i))"
done

echo ""
echo "=== Export TOYDB_HOSTS ==="
echo ""
echo "  export TOYDB_HOSTS=\"$HOSTS\""
echo ""
