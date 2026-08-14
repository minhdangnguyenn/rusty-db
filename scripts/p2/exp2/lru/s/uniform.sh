ID=${1:-1}
cd /opt/toydb
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
./target/release/workload $HOST_FLAG \
  --experiment exp2-lru-s-uniform --id "$ID" \
  --out-dir /opt/toydb/csv \
  read --rows 1000 --cache --cache-size 5000
