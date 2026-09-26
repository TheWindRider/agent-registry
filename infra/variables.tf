variable "project_id" {
  description = "GCP project ID where the registry and runtime resources will be deployed."
  type        = string
  default     = "gen-lang-client-0821611007"
}

variable "region" {
  description = "Primary GCP region for the registry and agent deployment."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Default compute zone used for compatibility with Terraform resources."
  type        = string
  default     = "us-central1-a"
}

variable "artifact_registry_repository_id" {
  description = "Artifact Registry repository name used for agent and registry container images."
  type        = string
  default     = "agent-registry"
}

variable "registry_service_name" {
  description = "Cloud Run service name for the central registry service."
  type        = string
  default     = "a2a-registry"
}

variable "registry_image" {
  description = "Optional registry image URI. Defaults to the registry image in the configured Artifact Registry repository."
  type        = string
  default     = null
  nullable    = true
}

variable "registry_max_instance_count" {
  description = "Maximum number of Cloud Run registry instances."
  type        = number
  default     = 10
}

variable "agent_service_name" {
  description = "Default name used for example agent services when deployed."
  type        = string
  default     = "example-agent"
}

variable "firestore_database_id" {
  description = "Firestore database ID to use for registry state."
  type        = string
  default     = "(default)"
}
