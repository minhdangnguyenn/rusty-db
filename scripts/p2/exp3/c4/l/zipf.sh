ID=${1:-1}
cd /opt/toydb
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
./target/release/workload $HOST_FLAG \
  --experiment exp3-c4-l-zipf --id "$ID" \
  --out-dir /opt/toydb/csv \
  -c 4 \
  read --rows 10000 --cache --dist zipf
