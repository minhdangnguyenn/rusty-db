# zipf distribution with default skew (1.0)
cargo run --release --bin workload -- --experiment read-s-zipf read --rows 1000 --dist zipf

# zipf with custom skew (higher = more concentrated)
# cargo run --release --bin workload -- --experiment read-s-zipf-skew read --rows 1000 --dist zipf --zipf-skew 1.5
