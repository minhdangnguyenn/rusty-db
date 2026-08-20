variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "cogent-dragon-451411-m4"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west3"
}

variable "zone" {
  description = "GCP zone within the region"
  type        = string
  default     = "europe-west3-c"
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "toydb"
}

variable "machine_type" {
  description = "GCE machine type for each node"
  type        = string
  default     = "e2-medium"
}

variable "disk_size_gb" {
  description = "Boot disk size per node (GB)"
  type        = number
  default     = 20
}

variable "client_machine_type" {
  description = "GCE machine type for the benchmark client VM"
  type        = string
  default     = "e2-medium"
}

variable "client_disk_size_gb" {
  description = "Boot disk size for the benchmark client VM (GB)"
  type        = number
  default     = 20
}

variable "client_cidrs" {
  description = "CIDR ranges allowed to connect to toyDB SQL ports"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
