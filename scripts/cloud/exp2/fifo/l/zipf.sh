ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment exp2-cache5000-fifo-l-zipf --id "$ID" read --rows 10000 --cache --cache-size 5000 --fifo --dist zipf
