resource "google_bigquery_dataset" "sample_manual_dataset" {
  project = "maneesh-mlops-sandbox-01"
  dataset_id = "sample_manual_dataset"
  location = "EU"
  max_time_travel_hours = 168
  is_case_insensitive = false

  access {
    role          = "WRITER"
    special_group = "projectWriters"
  }

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }

  access {
    role          = "OWNER"
    user_by_email = "kayamo5127@deapad.com"
  }

  access {
    role          = "READER"
    special_group = "projectReaders"
  }
}

import {
  to = google_bigquery_dataset.sample_manual_dataset
  id = "projects/maneesh-mlops-sandbox-01/datasets/sample_manual_dataset"
}
