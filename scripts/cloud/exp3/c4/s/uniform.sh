ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG \
--experiment exp3-c4-s-uniform \
-c 4 --id "$ID" read --rows 1000 --cache
