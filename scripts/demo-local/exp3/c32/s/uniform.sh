ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache5000-c32-s-uniform -c 32 --id "$ID" read --rows 1000 --cache --cache-size 5000
