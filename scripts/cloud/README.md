# Cloud Ops Scripts

All scripts run **LOCALLY** (on the dev machine) and drive the VMs over
`gcloud compute ssh`. `ZONE`/`PREFIX` default to `europe-west3-c`/`toydb`.

## A. Cluster panic recovery (`src/raft/log.rs:328: spliced entries below commit index`, "disconnected channel")

| # | Step | Where | Command |
|---|------|-------|---------|
| 1 | Diagnose: find panics in the journal | LOCAL | `bash scripts/cloud/check-panic.sh` |
| 2 | Sanitize: stop-all → wipe-all → start-all | LOCAL | `bash scripts/sanitize-cloud.sh` |
| 3 | Verify 5 nodes active, no new panics | LOCAL | `bash scripts/cloud/check-cluster.sh` |
| 4 | Verify SQL works (3s sanity read) | LOCAL (runs on node-1) | `bash scripts/cloud/verify-sql.sh` |
| 5 | Rerun the failed benchmark | **ON VM** (node-1) | `sudo -E bash scripts/phase2/...` |

> Never wipe nodes one at a time while the cluster is live — that is what
> causes the panic. Always use `sanitize-cloud.sh`.

## B. Benchmark hang (worker threads block forever, no summary CSV)

| # | Step | Where | Command |
|---|------|-------|---------|
| 1 | Kill the stuck workload on node-1 | LOCAL | `bash scripts/cloud/kill-workload.sh` |
| 2 | Rerun the benchmark with `--timeout 10` | **ON VM** (node-1) | `sudo -E bash scripts/phase2/...` |

## Reference: run a benchmark manually (ON VM, node-1)

```bash
export TOYDB_HOSTS="10.0.0.2:9601,10.0.0.3:9602,10.0.0.5:9603,10.0.0.6:9604,10.0.0.4:9605"
cd /opt/toydb
./target/release/workload -H $TOYDB_HOSTS \
  --experiment exp1-no-cache-l-uniform --id 1 \
  --out-dir /opt/toydb/csv --duration 30 --timeout 10 \
  read --rows 10000
```
