ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --duration 30 --experiment exp1-cache-s-zipf \
--id "$ID" read --rows 1000 --cache --dist zipf
