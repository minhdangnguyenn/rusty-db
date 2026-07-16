#!/usr/bin/env bash
ID="${1:-1}"
HOST_FLAG=""
[ -n "${TOYDB_HOSTS:-}" ] && HOST_FLAG="-H $TOYDB_HOSTS"
cargo run --release --bin workload -- $HOST_FLAG \
  --experiment exp3-nocache-c4-l-uniform \
  -c 4 --id "$ID" --duration 30 read --rows 10000
