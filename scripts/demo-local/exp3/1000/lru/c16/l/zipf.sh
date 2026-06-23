ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache1000-c16-l-zipf -c 16 --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 1000
