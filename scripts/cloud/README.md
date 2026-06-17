# External IPs for 5 nodes on GCP
```bash 
❯  ./tf.sh output node_external_ips
{
  "toydb-node-1" = "34.159.196.234"
  "toydb-node-2" = "34.40.126.153"
  "toydb-node-3" = "35.198.134.65"
  "toydb-node-4" = "35.198.133.143"
  "toydb-node-5" = "34.179.177.229"
}
```

# Run these scripts to run workloads in cloud from local machine
```bash 
export PATH="$HOME/google-cloud-sdk/bin:$PATH"

# declare all external IPs on the cloud -- get these ips using ./tf.sh output node_external_ips
export TOYDB_HOSTS="34.159.196.234:9601,34.40.126.153:9602,35.198.134.65:9603,35.198.133.143:9604,34.179.177.229:9605"

# no-cache
bash scripts/cloud/no-cache/uniform-s.sh 1

# cache
bash scripts/cloud/cache/uniform-s.sh 1
```
