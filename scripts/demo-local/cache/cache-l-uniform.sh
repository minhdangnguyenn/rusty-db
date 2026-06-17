ID=${1:-1}
cargo run --release --bin workload -- --experiment cache-l-uniform --id "$ID" read --rows 10000 --cache
