ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache1000-fifo-c8-l-uniform -c 8 --id "$ID" read --rows 10000 --cache --cache-size 1000 --fifo
