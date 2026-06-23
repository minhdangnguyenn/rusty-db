ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache250-c16-s-uniform -c 16 --id "$ID" read --rows 1000 --cache --cache-size 250
