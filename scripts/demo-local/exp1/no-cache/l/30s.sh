ID=${1:-1}
cargo run --release --bin workload -- -n 10000000 --duration 30 --experiment test-local-l-30s --id "$ID" read --rows 10000
