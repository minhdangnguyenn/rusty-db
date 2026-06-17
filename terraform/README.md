# toyDB — Terraform (GCP)

Deploy a 5-node toyDB cluster on Google Cloud, one VM per node.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) (Terraform runs in a container via `tf.sh`)
- A GCP service account key at `keys/gcp-key.json`
  (already present — contains a key for project `cogent-dragon-451411-m4`)

## Quick start

`tf.sh` wraps Terraform in Docker with `--network host` (needed to reach the Terraform registry) and mounts the GCP key.

```bash
# Initialise (already done — skip if .terraform/ exists).
./tf.sh init

# Preview what will be created.
./tf.sh plan

# Deploy (type "yes" when prompted).
./tf.sh apply

# See all outputs (IPs, connect commands).
./tf.sh output
```

## Commands

| Task               | Command                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Init               | `./tf.sh init`                                                                                                     |
| Plan               | `./tf.sh plan`                                                                                                     |
| Apply              | `./tf.sh apply`                                                                                                    |
| Get internal IPs   | `./tf.sh output node_internal_ips`                                                                                 |
| Get external IPs   | `./tf.sh output node_external_ips`                                                                                 |
| Connect to node 1  | `cargo run --bin toysql -- -H $(./tf.sh output -raw node_external_ips \| grep node-1 \| awk '{print $2}') -p 9601` |
| Destroy everything | `./tf.sh destroy`                                                                                                  |

## Configuration

Variables are in [`variables.tf`](variables.tf). Override via `-var`:

```bash
./tf.sh plan -var="machine_type=e2-small" -var="disk_size_gb=30"
```

Or create a `terraform.tfvars` file:

```hcl
machine_type = "e2-small"
disk_size_gb = 30
```

## Post-deploy: starting toyDB

1.  Get the internal IPs:

    ```bash
    ./tf.sh output node_internal_ips
    ```

2.  SSH into each node, create `/opt/toydb/toydb.yaml`. Example for node 1 (internal IP `10.0.0.2`):

    ```yaml
    id: 1
    data_dir: /opt/toydb/data
    listen_sql: 0.0.0.0:9601
    listen_raft: 0.0.0.0:9701
    peers:
        "2": 10.0.0.3:9702
        "3": 10.0.0.4:9703
        "4": 10.0.0.5:9704
        "5": 10.0.0.6:9705
    ```

    Adjust IPs, ports, and node IDs for each node.

3.  Start the server (the startup script already built the binary):

    ```bash
    cd /opt/toydb && RUST_LOG=info ./target/release/toydb -c toydb.yaml
    ```

## Architecture

| Resource                               | Count | Name pattern                    |
| -------------------------------------- | ----- | ------------------------------- |
| VPC                                    | 1     | `toydb-vpc`                     |
| Subnet (10.0.0.0/24)                   | 1     | `toydb-subnet`                  |
| Firewall — SSH (port 22)               | 1     | `toydb-allow-ssh`               |
| Firewall — SQL (ports 9601–9605)       | 1     | `toydb-allow-sql`               |
| Firewall — Raft (ports 9701–9705)      | 1     | `toydb-allow-raft`              |
| VM instances (e2-medium, Ubuntu 22.04) | 5     | `toydb-node-1` … `toydb-node-5` |

## Teardown

```bash
./tf.sh destroy
```

## I edited these configs for each Node to setup the peer to peer connections
```bash
❯ $HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-1 --zone europe-west3-c \
  --command 'sudo tee /opt/toydb/toydb.yaml > /dev/null' << 'EOF'
id: 1
data_dir: /opt/toydb/data
listen_sql: 0.0.0.0:9601
listen_raft: 0.0.0.0:9701
peers:
  "2": 10.0.0.14:9702
  "3": 10.0.0.12:9703
  "4": 10.0.0.16:9704
  "5": 10.0.0.13:9705
EOF
❯ $HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-2 --zone europe-west3-c \
  --command 'sudo tee /opt/toydb/toydb.yaml > /dev/null' << 'EOF'
id: 2
data_dir: /opt/toydb/data
listen_sql: 0.0.0.0:9602
listen_raft: 0.0.0.0:9702
peers:
  "1": 10.0.0.15:9701
  "3": 10.0.0.12:9703
  "4": 10.0.0.16:9704
  "5": 10.0.0.13:9705
EOF
❯ $HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-3 --zone europe-west3-c \
  --command 'sudo tee /opt/toydb/toydb.yaml > /dev/null' << 'EOF'
id: 3
data_dir: /opt/toydb/data
listen_sql: 0.0.0.0:9603
listen_raft: 0.0.0.0:9703
peers:
  "1": 10.0.0.15:9701
  "2": 10.0.0.14:9702
  "4": 10.0.0.16:9704
  "5": 10.0.0.13:9705
EOF
❯ $HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-4 --zone europe-west3-c \
  --command 'sudo tee /opt/toydb/toydb.yaml > /dev/null' << 'EOF'
id: 4
data_dir: /opt/toydb/data
listen_sql: 0.0.0.0:9604
listen_raft: 0.0.0.0:9704
peers:
  "1": 10.0.0.15:9701
  "2": 10.0.0.14:9702
  "3": 10.0.0.12:9703
  "5": 10.0.0.13:9705
EOF
❯ $HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-5 --zone europe-west3-c \
  --command 'sudo tee /opt/toydb/toydb.yaml > /dev/null' << 'EOF'
id: 5
data_dir: /opt/toydb/data
listen_sql: 0.0.0.0:9605
listen_raft: 0.0.0.0:9705
peers:
  "1": 10.0.0.15:9701
  "2": 10.0.0.14:9702
  "3": 10.0.0.12:9703
  "4": 10.0.0.16:9704
EOF
❯ for i in 1 2 3 4 5; do
  $HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-$i --zone europe-west3-c \
    --command 'sudo nohup /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml > /tmp/toydb.log 2>&1 &'
done

# check if the cluster run correctly on all nodes 
❯ export PATH="$HOME/google-cloud-sdk/bin:$PATH"
for i in 1 2 3 4 5; do
  echo "node-$i: $($HOME/google-cloud-sdk/bin/gcloud compute ssh toydb-node-$i --zone europe-west3-c \
    --command 'ps aux | grep toydb | grep -v grep' 2>/dev/null)"
done
node-1: root        5653  0.0  0.1  11900  5652 ?        S    08:49   0:00 sudo nohup /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
root        5654  0.1  0.1 753536  6464 ?        Sl   08:49   0:00 /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
node-2: root        5492  0.0  0.1  11904  5668 ?        S    08:49   0:00 sudo nohup /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
root        5493  0.1  0.1 753536  6644 ?        Sl   08:49   0:00 /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
node-3: root        5498  0.0  0.1  11904  5668 ?        S    08:49   0:00 sudo nohup /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
root        5499  0.1  0.1 753536  6456 ?        Sl   08:49   0:00 /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
node-4: root        5480  0.0  0.1  11896  5668 ?        S    08:49   0:00 sudo nohup /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
root        5481  0.1  0.1 753536  6424 ?        Sl   08:49   0:00 /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
node-5: root        5540  0.0  0.1  11896  5644 ?        S    08:49   0:00 sudo nohup /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
root        5541  0.1  0.1 753536  6492 ?        Sl   08:49   0:00 /opt/toydb/target/release/toydb -c /opt/toydb/toydb.yaml
```
