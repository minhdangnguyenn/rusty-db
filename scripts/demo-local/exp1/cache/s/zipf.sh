ID=${1:-1}
cargo run --release --bin workload -- --experiment exp1-cache-s-zipf --id "$ID" read --rows 1000 --cache --dist zipf
