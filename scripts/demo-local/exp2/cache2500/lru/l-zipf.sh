ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-large-lru-l-zipf --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 2500
