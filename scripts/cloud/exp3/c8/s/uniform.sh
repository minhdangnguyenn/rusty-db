ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- --experiment cloud-exp3-cache5000-c8-s-uniform -c 8 --id "$ID" read --rows 1000 --cache --cache-size 5000
