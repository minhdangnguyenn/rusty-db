ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-cache500-lru-l-uniform --id "$ID" read --rows 10000 --cache --cache-size 500
