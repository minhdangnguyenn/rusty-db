# provider "google" {
#   project = var.project_id
#   region  = var.region
# }

# data "google_client_openid_userinfo" "me" {}

# resource "google_compute_network" "vpc_network" {
#   name                    = "pams-network"
#   auto_create_subnetworks = true
# }

# resource "google_compute_subnetwork" "vpc_subnetwork" {
#   name          = "pams-subnet"
#   ip_cidr_range = "10.0.0.0/16"
#   region        = var.region
#   network       = google_compute_network.vpc_network.id
# }

# resource "google_compute_firewall" "allow_ssh" {
#   name          = "allow-ssh"
#   network       = google_compute_network.vpc_network.name
#   target_tags   = ["allow-ssh"]
#   source_ranges = ["0.0.0.0/0"]

#   allow {
#     protocol = "tcp"
#     ports    = ["22", "3000"] # If you need to access more ports add them here
#   }
# }

# resource "google_compute_instance" "server-instance" {
#   machine_type   = var.server_machine_type
#   name           = "instance-server"
#   desired_status = var.server_running && !var.stop_all ? "RUNNING" : "TERMINATED"
#   tags           = ["allow-ssh"]

#   boot_disk {
#     auto_delete = true
#     device_name = "instance-server"

#     initialize_params {
#       image = var.server_image
#       type  = "pd-standard"
#     }

#     mode = "READ_WRITE"
#   }

#   labels = {
#     ec-src = "vm_add-tf"
#   }

#   network_interface {
#     network    = google_compute_network.vpc_network.name
#     subnetwork = google_compute_subnetwork.vpc_subnetwork.name
#     network_ip = "10.0.0.2"

#     access_config {
#       network_tier = "PREMIUM"
#     }
#   }

#   scheduling {
#     automatic_restart   = false
#     on_host_maintenance = "TERMINATE"
#     preemptible         = var.is_server_using_spot_provisioning ? true : false
#     provisioning_model  = var.is_server_using_spot_provisioning ? "SPOT" : "STANDARD"
#   }

#   guest_accelerator {
#     type  = "nvidia-tesla-t4"
#     count = var.server_gpu_enabled ? 1 : 0
#   }

#   metadata = {
#     ssh-keys = "${var.ssh_username}:${file(var.ssh_pub_key_file_path)}"
#   }
# }

# resource "google_compute_instance" "client-instance" {
#   machine_type   = var.client_machine_type
#   name           = "instance-client-${count.index}"
#   count          = var.number_of_clients
#   desired_status = var.client_running && !var.stop_all ? "RUNNING" : "TERMINATED"
#   tags           = ["allow-ssh"]

#   boot_disk {
#     auto_delete = true
#     device_name = "instance-client-${count.index}"

#     initialize_params {
#       image = var.client_image
#       type  = "pd-standard"
#     }

#     mode = "READ_WRITE"
#   }

#   labels = {
#     ec-src = "vm_add-tf"
#   }

#   network_interface {
#     network    = google_compute_network.vpc_network.name
#     subnetwork = google_compute_subnetwork.vpc_subnetwork.name
#     network_ip = "10.0.0.${count.index + 3}"

#     access_config {
#       network_tier = "PREMIUM"
#     }
#   }

#   scheduling {
#     automatic_restart = false
#     #     on_host_maintenance = "TERMINATE" Causes an error for e-type instances
#     preemptible        = var.is_client_using_spot_provisioning ? true : false
#     provisioning_model = var.is_client_using_spot_provisioning ? "SPOT" : "STANDARD"
#   }

#   metadata = {
#     ssh-keys = "${var.ssh_username}:${file(var.ssh_pub_key_file_path)}"
#   }
# }
