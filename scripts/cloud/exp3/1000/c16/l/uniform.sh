ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp3-cache1000-c16-l-uniform --id "$ID" -c 16 read --rows 10000 --cache --cache-size 1000 
