ID=${1:-1}
cargo run --release --bin workload -- --experiment no-cache-read-l-zipf --id "$ID" read --rows 10000
