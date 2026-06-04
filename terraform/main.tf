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

# Startup script: install Rust and build toyDB on first boot
locals {
  startup_script = <<-SCRIPT
    #!/usr/bin/env bash
    set -euo pipefail

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq build-essential pkg-config libssl-dev

    if ! command -v rustc &>/dev/null; then
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
    fi

    source "$${HOME}/.cargo/env"

    if [ ! -d /opt/toydb ]; then
      git clone https://github.com/erikgrinaker/toydb /opt/toydb
    fi

    cd /opt/toydb
    git pull --ff-only origin main || true
    cargo build --release --bin toydb
  SCRIPT
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
  }

  depends_on = [
    google_compute_firewall.ssh,
    google_compute_firewall.sql,
    google_compute_firewall.raft,
  ]
}
