ID=${1:-1}
cargo run --release --bin workload -- --experiment no-cache-read-s-uniform --id "$ID" read --rows 1000
