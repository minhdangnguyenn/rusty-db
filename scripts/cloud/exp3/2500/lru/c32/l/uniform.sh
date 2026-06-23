ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- --experiment cloud-exp3-cache2500-c32-l-uniform -c 32 --id "$ID" read --rows 10000 --cache --cache-size 2500
