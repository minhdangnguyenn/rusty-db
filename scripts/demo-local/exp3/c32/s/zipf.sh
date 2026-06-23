ID=${1:-1}
cargo run --release --bin workload -- --experiment exp3-cache5000-c32-s-zipf -c 32 --id "$ID" read --rows 1000 --cache --dist zipf --cache-size 5000
