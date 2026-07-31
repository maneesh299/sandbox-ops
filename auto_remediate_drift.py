#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

# Set GCP parameters
PROJECT_ID = "maneesh-mlops-sandbox-01"
LOCATION = "europe-west2"

# 1. Read existing Terraform configurations to find tracked datasets
tf_dir = Path(__file__).resolve().parent
existing_tf_files = list(tf_dir.glob("*.tf"))
tracked_datasets = set()

for tf_file in existing_tf_files:
    content = tf_file.read_text()
    import re
    # Match dataset_id assignments
    for m in re.finditer(r'dataset_id\s*=\s*"([^"]+)"', content):
        tracked_datasets.add(m.group(1))

print(f"🔍 Currently tracked datasets in Terraform: {list(tracked_datasets)}")

# 2. Query GCP for ALL active BigQuery datasets in the project
print("🛰️  Scanning live BigQuery datasets in GCP...")
try:
    bq_list_proc = subprocess.run(
        ["bq", "ls", f"--project_id={PROJECT_ID}", "--format=json"],
        capture_output=True,
        text=True,
        check=True
    )
    live_datasets_data = json.loads(bq_list_proc.stdout)
except Exception as e:
    print(f"❌ Failed to query BigQuery datasets: {e}")
    sys.exit(1)

live_datasets = [d.get("datasetReference", {}).get("datasetId") for d in live_datasets_data]
print(f"🌐 Live datasets found in GCP: {live_datasets}")

# 3. Detect untracked (drifted) datasets
drifted_datasets = [d for d in live_datasets if d and d not in tracked_datasets]
if not drifted_datasets:
    print("✅ No drifted datasets detected! Everything in GCP matches your Terraform config.")
    sys.exit(0)

print(f"⚠️  Drift Detected! The following datasets are NOT in Terraform: {drifted_datasets}")

# 4. Fetch JSON metadata for the first drifted dataset to remediate
target_dataset = drifted_datasets[0]
print(f"📝 Fetching JSON metadata for untracked dataset: {target_dataset}...")

try:
    bq_desc_proc = subprocess.run(
        ["bq", "show", "--format=json", f"{PROJECT_ID}:{target_dataset}"],
        capture_output=True,
        text=True,
        check=True
    )
    dataset_metadata_str = bq_desc_proc.stdout
except Exception as e:
    print(f"❌ Failed to describe dataset: {e}")
    sys.exit(1)

# 5. Call Gemini AI via Vertex AI to generate the Terraform code
print("🧠 Sending metadata to Vertex AI Gemini Pro...")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Using gemini-1.5-flash for rapid, lightweight generation
    model = GenerativeModel("gemini-1.5-flash")

    prompt = f"""
You are a Principal Cloud and Infrastructure Engineer specializing in Google Cloud and Terraform (IaC).
We have detected a manually created BigQuery dataset in our console that needs to be imported into Terraform.

Below is the live JSON metadata of the drifted dataset:
{dataset_metadata_str}

Please generate the exact Terraform HCL code to remediate this drift.
Conform to HashiCorp best practices and include:
1. A standard `google_bigquery_dataset` resource block named "{target_dataset}". Include its standard fields (dataset_id, friendly_name, description, location, labels) as defined in the metadata.
2. A declarative `import` block (available in Terraform >= 1.5) to import the live resource into the resource state automatically.

Output ONLY the exact, raw Terraform code. Do not wrap it in formatting text other than hcl block markers.
Do not write explanations, markdown prose, or conversational preambles.
"""

    response = model.generate_content(prompt)
    generated_code = response.text.strip()
    
    # Strip markdown block formatting if present
    if generated_code.startswith("```"):
        lines = generated_code.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        generated_code = "\n".join(lines).strip()

except ImportError:
    print("❌ 'google-cloud-aiplatform' package is not installed. Run 'pip install google-cloud-aiplatform'")
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to call Gemini API: {e}")
    sys.exit(1)

# 6. Write the generated code to a new drifted_resources.tf file
drift_file = tf_dir / "drifted_resources.tf"
print(f"💾 Saving auto-generated remediation code to {drift_file.name}...")
try:
    drift_file.write_text(generated_code + "\n", encoding="utf-8")
    print(f"🎉 Success! Review the generated code in '{drift_file.name}' and push to GitHub to auto-import and align state!")
    print("\n--- Generated Code Preview ---")
    print(generated_code)
    print("------------------------------")
except Exception as e:
    print(f"❌ Failed to save file: {e}")
