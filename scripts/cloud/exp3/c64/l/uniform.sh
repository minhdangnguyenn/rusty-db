ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG \
--experiment exp3-c64-l-uniform \
-c 64 --id "$ID" read --rows 10000 --cache
