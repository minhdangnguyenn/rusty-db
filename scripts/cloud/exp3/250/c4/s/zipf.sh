ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp3-cache250-c4-s-zipf --id "$ID" -c 4 read --rows 1000 --cache --cache-size 250 --dist zipf
