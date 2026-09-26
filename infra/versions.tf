terraform {
  required_version = ">= 1.6.0"

  backend "gcs" {
    bucket = "gen-lang-client-0821611007-terraform-state"
    prefix = "agent-registry"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}
