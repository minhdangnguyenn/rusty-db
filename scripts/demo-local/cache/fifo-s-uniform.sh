ID=${1:-1}
cargo run --release --bin workload -- --experiment cache-s-fifo-uniform --id "$ID" read --rows 1000 --cache --fifo
