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
: "${TF_STATE_BUCKET:?Set TF_STATE_BUCKET in .env}"
: "${TF_STATE_PREFIX:?Set TF_STATE_PREFIX in .env}"

command -v gcloud >/dev/null || { echo "gcloud CLI is required" >&2; exit 1; }

BUCKET_URI="gs://${TF_STATE_BUCKET}"

if gcloud storage buckets describe "${BUCKET_URI}" --project="${GCP_PROJECT}" >/dev/null 2>&1; then
  echo "Terraform state bucket already exists: ${BUCKET_URI}"
else
  gcloud storage buckets create "${BUCKET_URI}" \
    --project="${GCP_PROJECT}" \
    --location="${GCP_REGION}" \
    --uniform-bucket-level-access
fi

gcloud storage buckets update "${BUCKET_URI}" \
  --uniform-bucket-level-access \
  --versioning

echo "Terraform state bucket is ready: ${BUCKET_URI}"
echo "Terraform backend prefix: ${TF_STATE_PREFIX}"
