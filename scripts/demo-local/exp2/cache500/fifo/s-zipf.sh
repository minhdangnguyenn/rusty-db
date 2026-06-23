ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-cache500-fifo-s-zipf --id "$ID" read --rows 1000 --cache --dist zipf --cache-size 500 --fifo
