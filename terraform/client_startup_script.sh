#!/usr/bin/env bash
set -euo pipefail
export HOME=/root

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential pkg-config libssl-dev

if ! command -v rustc &>/dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
    source "$HOME/.cargo/env"
fi

if [ ! -d /opt/toydb ]; then
    git clone https://github.com/minhdangnguyenn/rusty-db /opt/toydb
fi

cd /opt/toydb
git pull --ff-only || true

if [ ! -f /opt/toydb/target/release/workload ]; then
    cargo build --release --bin workload
fi

SQL_HOSTS=$(curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/attributes/sql_hosts)
cat > /etc/profile.d/toydb-hosts.sh << EOF
export TOYDB_HOSTS="$SQL_HOSTS"
EOF
