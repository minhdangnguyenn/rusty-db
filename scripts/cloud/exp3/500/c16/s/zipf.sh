ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp3-cache500-c16-s-zipf --id "$ID" -c 16 read --rows 1000 --cache --cache-size 500 --dist zipf
