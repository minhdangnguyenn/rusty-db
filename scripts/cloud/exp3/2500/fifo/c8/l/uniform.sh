ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- --experiment cloud-exp3-cache2500-fifo-c8-l-uniform -c 8 --id "$ID" read --rows 10000 --cache --cache-size 2500 --fifo
