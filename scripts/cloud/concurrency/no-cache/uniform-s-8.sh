ID=${1:-1}
HOST_FLAG=""

[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG \
  --experiment cloud-no-cache-concurrency-s-uniform --id "$ID" -c 8 read --rows 1000
