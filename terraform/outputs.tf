output "node_internal_ips" {
  description = "Internal IPs of each node (for node-to-node Raft config)"
  value = {
    for i, inst in google_compute_instance.db_nodes :
    inst.name => inst.network_interface[0].network_ip
  }
}

output "node_external_ips" {
  description = "External IPs of each node (for toysql clients)"
  value = {
    for i, inst in google_compute_instance.db_nodes :
    inst.name => inst.network_interface[0].access_config[0].nat_ip
  }
}

output "connect_commands" {
  description = "Convenience commands for connecting to each node"
  value = {
    for i, inst in google_compute_instance.db_nodes :
    "Node ${i + 1}" => "cargo run --bin toysql -- -H ${inst.network_interface[0].access_config[0].nat_ip} -p ${9600 + i + 1}"
  }
}
