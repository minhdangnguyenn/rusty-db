ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- --experiment cloud-exp3-cache2500-fifo-c32-l-zipf -c 32 --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 2500 --fifo
