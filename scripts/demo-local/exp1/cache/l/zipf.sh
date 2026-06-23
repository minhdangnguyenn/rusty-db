ID=${1:-1}
cargo run --release --bin workload -- --experiment exp1-cache-l-zipf --id "$ID" read --rows 10000 --cache --dist zipf
