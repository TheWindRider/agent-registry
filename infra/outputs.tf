output "project_id" {
  description = "GCP project ID for the registry deployment."
  value       = var.project_id
}

output "region" {
  description = "Primary deployment region."
  value       = var.region
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository that stores registry and agent images."
  value       = google_artifact_registry_repository.agent_images.name
}

output "firestore_database_name" {
  description = "Firestore database path created for registry state."
  value       = google_firestore_database.agent_registry.name
}

output "registry_url" {
  description = "Cloud Run URL for the central registry service."
  value       = module.registry_service.service_url
}

output "agent_url" {
  description = "Expected Cloud Run URL for the example agent service once deployed via the agent module."
  value       = "https://${var.agent_service_name}-${var.project_id}.run.app"
}
