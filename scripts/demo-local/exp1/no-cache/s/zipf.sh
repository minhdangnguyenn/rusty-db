ID=${1:-1}
cargo run --release --bin workload -- --experiment exp1-no-cache-s-zipf --id "$ID" read --rows 1000 --dist zipf
