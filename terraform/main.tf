terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  node_count = 5
  sql_base   = 9600
  raft_base  = 9700
}

# VPC network
resource "google_compute_network" "main" {
  name                    = "${var.prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.prefix}-subnet"
  network       = google_compute_network.main.id
  region        = var.region
  ip_cidr_range = "10.0.0.0/24"
}

# Firewall: SSH from anywhere (for provisioning)
resource "google_compute_firewall" "ssh" {
  name    = "${var.prefix}-allow-ssh"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["${var.prefix}-node"]
}

# Firewall: toyDB SQL clients (from anywhere)
resource "google_compute_firewall" "sql" {
  name    = "${var.prefix}-allow-sql"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [for i in range(1, local.node_count + 1) : tostring(local.sql_base + i)]
  }

  source_ranges = var.client_cidrs
  target_tags   = ["${var.prefix}-node"]
}

# Firewall: toyDB Raft (inter-node, internal traffic only)
resource "google_compute_firewall" "raft" {
  name    = "${var.prefix}-allow-raft"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [for i in range(1, local.node_count + 1) : tostring(local.raft_base + i)]
  }

  source_ranges = ["10.0.0.0/24"]
  target_tags   = ["${var.prefix}-node"]
}

# static internal IPs for each node
resource "google_compute_address" "internal" {
  count        = local.node_count
  name         = "${var.prefix}-node-${count.index + 1}-internal"
  subnetwork   = google_compute_subnetwork.main.self_link
  address_type = "INTERNAL"
  region       = var.region
}

locals {
  startup_script = file("${path.module}/startup_script.sh")
}

# 5 VM instances
resource "google_compute_instance" "db_nodes" {
  count        = local.node_count
  name         = "${var.prefix}-node-${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["${var.prefix}-node"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.disk_size_gb
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.main.self_link

    access_config {
      # Ephemeral public IP
    }
  }

  service_account {
    scopes = ["cloud-platform"]
  }

  metadata = {
    startup-script = local.startup_script
    node_id        = count.index + 1
    my_ip          = google_compute_address.internal[count.index].address
    peer_ips = jsonencode({
      for i in range(local.node_count) :
      format("%d", i + 1) => "${google_compute_address.internal[i].address}:${local.raft_base + i + 1}"
    })
  }

  depends_on = [
    google_compute_firewall.ssh,
    google_compute_firewall.sql,
    google_compute_firewall.raft,
  ]
}
