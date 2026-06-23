ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache1000-fifo-c16-l-uniform -c 16 --id "$ID" read --rows 10000 --cache --cache-size 1000 --fifo
