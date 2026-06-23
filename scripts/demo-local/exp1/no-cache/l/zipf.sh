ID=${1:-1}
cargo run --release --bin workload -- --experiment exp1-no-cache-l-zipf --id "$ID" read --rows 10000 --dist zipf
