ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache5000-c8-l-uniform -c 8 --id "$ID" read --rows 10000 --cache --cache-size 5000
