ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-cache1000-lru-l-zipf --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 1000
