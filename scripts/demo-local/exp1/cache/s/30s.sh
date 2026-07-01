ID=${1:-1}
cargo run --release --bin workload -- -n 10000000 --duration 30 --experiment test-local-s-30s --id "$ID" read --rows 1000 --cache
