ID=${1:-1}
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- -H "$TOYDB_HOSTS" --experiment exp1-cache-s-txns30_0000 --id 1 -n 30000000 read --rows 1000 --cache
