ID=${1:-1}
HOST_FLAG=""

[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG \
  --experiment cloud-cache-concurrency-l-uniform --id "$ID" -c 24 read --rows 10000 --cache
