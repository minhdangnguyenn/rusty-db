#!/bin/bash

# Run Terraform using the official Docker image
# - Passes down all arguments (like init, plan, apply) using "$@"
# - Mounts the current directory into the container
# - Inject the GCP service account credentials safely via environment variable
docker run -i --rm --network host \
  -v "$(pwd)":/workspace \
  -e GOOGLE_APPLICATION_CREDENTIALS=/workspace/keys/gcp-key.json \
  -w /workspace \
  hashicorp/terraform:latest "$@"
