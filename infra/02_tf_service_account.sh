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
: "${GCP_TERRAFORM_SERVICE_ACCOUNT:?Set GCP_TERRAFORM_SERVICE_ACCOUNT in .env}"

command -v gcloud >/dev/null || { echo "gcloud CLI is required" >&2; exit 1; }

SERVICE_ACCOUNT_NAME="${GCP_TERRAFORM_SERVICE_ACCOUNT%@*}"
SERVICE_ACCOUNT_EMAIL="${GCP_TERRAFORM_SERVICE_ACCOUNT}"

if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" \
  --project="${GCP_PROJECT}" >/dev/null 2>&1; then
  echo "Terraform service account already exists: ${SERVICE_ACCOUNT_EMAIL}"
else
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --project="${GCP_PROJECT}" \
    --display-name="Terraform provisioning" \
    --description="Provisioner for agent registry infrastructure"
fi

# Bootstrap permissions for Terraform root, intentionally broad 
for ROLE in \
  roles/serviceusage.serviceUsageAdmin \
  roles/run.admin \
  roles/artifactregistry.admin \
  roles/datastore.owner \
  roles/secretmanager.admin \
  roles/storage.admin \
  roles/cloudbuild.builds.editor \
  roles/iam.serviceAccountAdmin \
  roles/iam.serviceAccountUser \
  roles/resourcemanager.projectIamAdmin
 do
  gcloud projects add-iam-policy-binding "${GCP_PROJECT}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="${ROLE}" \
    --quiet >/dev/null
done

# Let the currently authenticated human run Terraform via ADC impersonation
USER_EMAIL="$(gcloud config get-value account 2>/dev/null)"
if [[ -z "${USER_EMAIL}" || "${USER_EMAIL}" == "(unset)" ]]; then
  echo "No active gcloud account found. Run: gcloud auth login" >&2
  exit 1
fi

gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_EMAIL}" \
  --project="${GCP_PROJECT}" \
  --member="user:${USER_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet >/dev/null

echo "Terraform service account is ready: ${SERVICE_ACCOUNT_EMAIL}"
echo "Impersonation granted to: ${USER_EMAIL}"
