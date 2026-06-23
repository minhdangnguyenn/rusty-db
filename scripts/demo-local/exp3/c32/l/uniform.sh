ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache5000-c32-l-uniform -c 32 --id "$ID" read --rows 10000 --cache --cache-size 5000
