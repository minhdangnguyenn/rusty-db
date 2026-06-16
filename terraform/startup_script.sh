#!/usr/bin/env bash
set -euo pipefail
export HOME=/root

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential pkg-config libssl-dev

if ! command -v rustc &>/dev/null; then
	# install rust on each VM
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
    source "$HOME/.cargo/env"
fi

if [ ! -d /opt/toydb ]; then
    git clone https://github.com/minhdangnguyenn/rusty-db /opt/toydb
fi

cd /opt/toydb
git pull --ff-only || true
cargo build --release --bin toydb
cargo build --release --bin workload

NODE_ID=$(curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/attributes/node_id)
MY_IP=$(curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/attributes/my_ip)
PEER_IPS=$(curl -s -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/attributes/peer_ips)

export NODE_ID MY_IP PEER_IPS
mkdir -p /opt/toydb/data

python3 -c "
import json, os
nid = os.environ['NODE_ID']
peers = json.loads(os.environ['PEER_IPS'])
with open('/opt/toydb/toydb.yaml', 'w') as f:
    f.write(f'id: {nid}\n')
    f.write(f'data_dir: /opt/toydb/data\n')
    f.write(f'listen_sql: 0.0.0.0:{9600 + int(nid)}\n')
    f.write(f'listen_raft: 0.0.0.0:{9700 + int(nid)}\n')
    f.write('peers:\n')
    for k, v in peers.items():
        if k != nid:
            f.write(f'  \"{k}\": {v}\n')
"
