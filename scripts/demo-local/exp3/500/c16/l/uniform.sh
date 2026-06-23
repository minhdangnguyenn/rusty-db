ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache500-c16-l-uniform -c 16 --id "$ID" read --rows 10000 --cache --cache-size 500
