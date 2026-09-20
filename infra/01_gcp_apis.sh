#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

: "${GCP_PROJECT:?Set GCP_PROJECT in .env}"
: "${GCP_REGION:?Set GCP_REGION in .env}"

command -v gcloud >/dev/null || { echo "gcloud CLI is required" >&2; exit 1; }

echo "Configuring project ${GCP_PROJECT} in region ${GCP_REGION}"
gcloud config set project "${GCP_PROJECT}"
gcloud config set run/region "${GCP_REGION}"

# This list includes APIs needed by the Terraform root and later deployments.
gcloud services enable \
  serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com \
  --project="${GCP_PROJECT}"

echo "Required APIs are enabled for ${GCP_PROJECT}."
