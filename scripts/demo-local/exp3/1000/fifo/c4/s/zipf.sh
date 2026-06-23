ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache1000-fifo-c4-s-zipf -c 4 --id "$ID" read --rows 1000 --cache --dist zipf --cache-size 1000 --fifo
