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

## Post-deploy

The startup script on each VM:
- Installs Rust, clones the repo, builds `toydb` and `workload`
- Generates `/opt/toydb/toydb.yaml` with correct internal IPs (static reservation)
- Installs a `systemd` service so `toydb` auto-starts on boot

**1. Wait for all nodes to report `active`:**

```bash
for i in 1 2 3 4 5; do
  gcloud compute ssh toydb-node-$i --zone europe-west3-c \
    --command "systemctl is-active toydb"
done
```

**2. Get the external IPs:**

```bash
gcloud compute instances list --zones=europe-west3-c \
  --format="table(name,networkInterfaces[0].accessConfigs[0].natIP)"
```

**3. Export `TOYDB_HOSTS`:**

```bash
export TOYDB_HOSTS="<ext-ip-1>:9601,<ext-ip-2>:9602,<ext-ip-3>:9603,<ext-ip-4>:9604,<ext-ip-5>:9605"
```

**4. Run workloads (see `../scripts/cloud/`):**

```bash
# Quick connectivity test
cargo run --release --bin workload -- -H "$TOYDB_HOSTS" \
  --experiment test-connect read --rows 1 -n 1

# Full benchmarks
bash ../scripts/cloud/no-cache/uniform-s.sh 1
bash ../scripts/cloud/cache/uniform-s.sh 1
```

**5. Or use the automation script:**

```bash
bash ../scripts/cloud/after-deploy.sh
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
