ID=${1:-1}
cd /opt/toydb
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
./target/release/workload $HOST_FLAG \
  --experiment exp3-nocache-c4-s-uniform --id "$ID" \
  --out-dir /opt/toydb/csv \
  -c 4 --duration 30 \
  read --rows 1000
