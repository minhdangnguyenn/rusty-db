## Output of terraform apply

```bash
connect_commands = {
  "Node 1" = "cargo run --bin toysql -- -H 34.107.42.7 -p 9601"
  "Node 2" = "cargo run --bin toysql -- -H 34.141.67.247 -p 9602"
  "Node 3" = "cargo run --bin toysql -- -H 34.89.135.54 -p 9603"
  "Node 4" = "cargo run --bin toysql -- -H 34.159.236.102 -p 9604"
  "Node 5" = "cargo run --bin toysql -- -H 35.246.179.56 -p 9605"
}
node_external_ips = {
  "toydb-node-1" = "34.107.42.7"
  "toydb-node-2" = "34.141.67.247"
  "toydb-node-3" = "34.89.135.54"
  "toydb-node-4" = "34.159.236.102"
  "toydb-node-5" = "35.246.179.56"
}
node_internal_ips = {
  "toydb-node-1" = "10.0.0.9"
  "toydb-node-2" = "10.0.0.10"
  "toydb-node-3" = "10.0.0.7"
  "toydb-node-4" = "10.0.0.11"
  "toydb-node-5" = "10.0.0.8"
}
```
