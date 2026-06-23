ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG --experiment cloud-exp1-no-cache-s-zipf --id "$ID" read --rows 1000  --dist zipf
