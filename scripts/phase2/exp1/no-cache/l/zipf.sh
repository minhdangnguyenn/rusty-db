ID=${1:-1}
cd /opt/toydb
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
./target/release/workload $HOST_FLAG \
  --experiment exp1-no-cache-l-zipf --id "$ID" \
  --out-dir /opt/toydb/csv \
  --duration 30 \
  read --rows 10000 --dist zipf
