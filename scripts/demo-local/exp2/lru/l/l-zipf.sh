ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-cache5000-lru-l-zipf --id "$ID" read --rows 10000 --cache --cache-size 5000  --dist zipf
