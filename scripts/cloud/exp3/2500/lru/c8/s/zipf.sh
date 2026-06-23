ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- --experiment cloud-exp3-cache2500-c8-s-zipf -c 8 --id "$ID" read --rows 1000 --cache --dist zipf --cache-size 2500
