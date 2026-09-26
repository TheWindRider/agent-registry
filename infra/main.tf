locals {
  required_apis = toset([
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "iamcredentials.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each = local.required_apis

  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "agent_images" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "Container images for the A2A registry and deployed agents."
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_firestore_database" "agent_registry" {
  project     = var.project_id
  name        = var.firestore_database_id
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required]
}

module "registry_service" {
  source = "./modules/registry-service"

  project_id         = var.project_id
  region             = var.region
  service_name       = var.registry_service_name
  container_image    = coalesce(var.registry_image, "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository_id}/registry:latest")
  service_account_id = "a2a-registry"
  max_instance_count = var.registry_max_instance_count

  depends_on = [
    google_artifact_registry_repository.agent_images,
    google_firestore_database.agent_registry,
  ]
}
