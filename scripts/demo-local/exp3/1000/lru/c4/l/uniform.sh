ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache1000-c4-l-uniform -c 4 --id "$ID" read --rows 10000 --cache --cache-size 1000
