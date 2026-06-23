ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache1000-fifo-c8-s-uniform -c 8 --id "$ID" read --rows 1000 --cache --cache-size 1000 --fifo
