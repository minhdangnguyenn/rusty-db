ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp2-cache500-fifo-l-uniform --id "$ID" read --rows 10000 --cache --cache-size 500 --fifo 
