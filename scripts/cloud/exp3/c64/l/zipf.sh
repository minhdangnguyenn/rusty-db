ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp3-cache5000-c64-l-zipf -c 64 --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 5000
