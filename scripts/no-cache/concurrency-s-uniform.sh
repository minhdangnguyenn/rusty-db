ID=${1:-1}
cargo run --release --bin workload -- --experiment no-cache-concurrency-s-uniform --id "$ID" -c 24 read --rows 1000
