ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-cache1000-fifo-l-uniform --id "$ID" read --rows 1000 --cache --cache-size 1000 --fifo
