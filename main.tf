terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "maneesh-mlops-sandbox-01-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = "maneesh-mlops-sandbox-01"
  region  = "europe-west2"
}

# --- 1. GCS Bucket for Pipeline Artifacts ---
resource "google_storage_bucket" "ml_pipeline_artifacts" {
  name                        = "maneesh-mlops-sandbox-01-ml-artifacts"
  location                    = "europe-west2"
  force_destroy               = true
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# --- 2. BigQuery Dataset for ML Training Features ---
resource "google_bigquery_dataset" "ml_features" {
  dataset_id                  = "ml_feature_store_sandbox"
  friendly_name               = "ML Feature Store Sandbox"
  description                 = "Contains historical features and targets for model training"
  location                    = "europe-west2"
  default_table_expiration_ms = 31536000000 # 1 Year

  labels = {
    env  = "sandbox"
    team = "mlops"
  }
}

# --- 3. Custom Service Account for Vertex AI Pipeline ---
resource "google_service_account" "vertex_pipeline_sa" {
  account_id   = "vertex-pipeline-runner"
  display_name = "Vertex AI Pipeline Service Account"
}

# --- 4. Least Privilege IAM Bindings ---
# GCS permissions for pipeline artifacts
resource "google_storage_bucket_iam_member" "pipeline_gcs_access" {
  bucket = google_storage_bucket.ml_pipeline_artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.vertex_pipeline_sa.email}"
}

# BigQuery Read access to fetch training data
resource "google_bigquery_dataset_iam_member" "pipeline_bq_read" {
  dataset_id = google_bigquery_dataset.ml_features.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.vertex_pipeline_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "pipeline_bq_user" {
  dataset_id = google_bigquery_dataset.ml_features.dataset_id
  role       = "roles/bigquery.user"
  member     = "serviceAccount:${google_service_account.vertex_pipeline_sa.email}"
}

# Vertex AI Runner permissions
resource "google_project_iam_member" "pipeline_vertex_runner" {
  project = "maneesh-mlops-sandbox-01"
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.vertex_pipeline_sa.email}"
}

# --- 5. Vertex AI Endpoint for Online Predictions ---
resource "google_vertex_ai_endpoint" "online_predictor" {
  name         = "prediction-endpoint-sandbox"
  display_name = "Model Prediction Endpoint - Sandbox"
  location     = "europe-west2"
  description  = "Managed endpoint for real-time model inferences"

  labels = {
    env  = "sandbox"
    team = "mlops"
  }
}
