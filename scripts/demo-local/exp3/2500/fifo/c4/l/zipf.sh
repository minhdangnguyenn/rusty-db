ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache2500-fifo-c4-l-zipf -c 4 --id "$ID" read --rows 10000 --cache --dist zipf --cache-size 2500 --fifo
