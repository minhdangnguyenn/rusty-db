ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp3-cache1000-fifo-c32-l-uniform --id "$ID" -c 32 read --rows 10000 --cache --cache-size 1000  --fifo
