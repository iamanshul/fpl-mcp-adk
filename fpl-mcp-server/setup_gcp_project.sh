#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Load Configuration ---
# Load variables from the local config file.
# This allows the main script to be committed to Git without secrets.
if [ -f "$(dirname "$0")/setup_config.sh" ]; then
    source "$(dirname "$0")/setup_config.sh"
else
    echo "Error: Configuration file setup_config.sh not found."
    echo "Please copy setup_config.sh.example to setup_config.sh and fill in your details."
    exit 1
fi

# --- Derived Variables ---
SERVICE_ACCOUNT_FULL_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"


echo "--- Setting up Google Cloud Project: ${PROJECT_ID} ---"

# 1. Set the active Google Cloud project (if not already set)
echo "Setting active gcloud project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

# 2. Enable necessary Google Cloud APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    logging.googleapis.com \
    iam.googleapis.com \
    firestore.googleapis.com \
    --project "${PROJECT_ID}" # Ensure APIs are enabled for the specific project

# 3. Create Artifact Registry repository (idempotent - safe to run multiple times)
echo "Creating Artifact Registry repository '${REPO_NAME}' in '${REGION}'..."
gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Repository for FPL MCP Server images" \
    --project "${PROJECT_ID}" \
    --async || true # Use --async and || true to prevent script from failing if it already exists

# Wait a moment for repository creation if needed, though 'create' usually blocks for a bit.
echo "Ensuring Artifact Registry repository is ready..."
gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project "${PROJECT_ID}" > /dev/null 2>&1 || { echo "Repository not found, try again or check permissions."; exit 1; }


# 4. Grant Cloud Build service account necessary permissions
echo "Granting Cloud Build service account permissions for project ${PROJECT_ID}..."

# Grant the core Cloud Build Service Account role (for building images, pulling source, pushing logs)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CLOUD_BUILD_SA_EMAIL}" \
  --role="roles/cloudbuild.builds.builder" \
  --project "${PROJECT_ID}" \
  --condition=None

# Grant Logs Writer for Cloud Build logs
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CLOUD_BUILD_SA_EMAIL}" \
  --role="roles/logging.logWriter" \
  --project "${PROJECT_ID}" \
  --condition=None

# Grant Artifact Registry Writer (for pushing images from Cloud Build to AR)
gcloud artifacts repositories add-iam-policy-binding "${REPO_NAME}" \
  --location="${REGION}" \
  --member="serviceAccount:${CLOUD_BUILD_SA_EMAIL}" \
  --role="roles/artifactregistry.writer" \
  --project "${PROJECT_ID}" \
  --condition=None


# 5. Create a dedicated service account for Cloud Run (if it doesn't exist)
echo "Creating Cloud Run service account '${SERVICE_ACCOUNT_NAME}'..."
gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="FPL MCP Server Cloud Run Service Account" \
    --project "${PROJECT_ID}" || true # Idempotent

# 6. Grant necessary permissions to the Cloud Run service account itself
echo "Granting permissions to Cloud Run service account '${SERVICE_ACCOUNT_FULL_EMAIL}' (for your app's runtime needs)..."

# Permissions for Firestore access (roles/datastore.user is for Datastore Mode; for Native Firestore, consider more granular roles)
# Assuming Native Firestore, add Firestore Data Editor or Contributor. If Datastore Mode, use roles/datastore.user.
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_FULL_EMAIL}" \
  --role="roles/datastore.user" \ # OR roles/firestore.datastoreEditor if you have Native Firestore
  --project "${PROJECT_ID}" \
  --condition=None

# For calling Google Gemini API (if your app directly calls it)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_FULL_EMAIL}" \
  --role="roles/aiplatform.user" \
  --project "${PROJECT_ID}" \
  --condition=None
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_FULL_EMAIL}" \
  --role="roles/serviceusage.serviceUsageConsumer" \
  --project "${PROJECT_ID}" \
  --condition=None

# (Optional) For accessing secrets from Secret Manager (if used)
# gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
#   --member="serviceAccount:${SERVICE_ACCOUNT_FULL_EMAIL}" \
#   --role="roles/secretmanager.secretAccessor" \
#   --project "${PROJECT_ID}" \
#   --condition=None


# 7. Grant the DEPLOYING USER permission to 'act as' the Cloud Run service account
# This is the permission that was causing your latest error.
echo "Granting '${DEPLOYING_USER_EMAIL}' permission to act as '${SERVICE_ACCOUNT_FULL_EMAIL}'..."
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_FULL_EMAIL}" \
  --member="user:${DEPLOYING_USER_EMAIL}" \
  --role="roles/iam.serviceAccountUser" \
  --project "${PROJECT_ID}" # Target project for the service account


# 8. Grant the DEPLOYING USER permission to deploy Cloud Run services
echo "Granting '${DEPLOYING_USER_EMAIL}' permission to deploy to Cloud Run..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="user:${DEPLOYING_USER_EMAIL}" \
  --role="roles/run.admin" \ # Cloud Run Admin role for the deploying user
  --project "${PROJECT_ID}" \
  --condition=None


echo "Google Cloud Project setup complete. You can now build and deploy."