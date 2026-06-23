ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache2500-c32-l-zipf -c 32 --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 2500
