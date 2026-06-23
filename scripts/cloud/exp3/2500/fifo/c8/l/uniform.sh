ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp3-cache2500-fifo-c8-l-uniform --id "$ID" -c 8 read --rows 10000 --cache --cache-size 2500  --fifo
