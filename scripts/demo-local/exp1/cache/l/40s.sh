ID=${1:-1}
cargo run --release --bin workload -- -n 10000000 --duration 40 --experiment test-local-l-40s --id "$ID" read --rows 10000 --cache
