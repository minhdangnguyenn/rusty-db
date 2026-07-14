#!/usr/bin/env bash
ID="${1:-1}"
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG \
  --experiment exp3-nocache-c32-l-zipf \
  -c 32 --id "$ID" read --rows 10000 --duration 30 --dist zipf
