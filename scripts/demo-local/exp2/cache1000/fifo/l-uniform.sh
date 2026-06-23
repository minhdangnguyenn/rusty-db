ID=${1:-1}
cargo run --release --bin workload -- --experiment exp2-small-fifo-l-uniform --id "$ID" read --rows 10000 --cache --cache-size 1000 --fifo
