#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

if [ -f ../.env ]; then
  source ../.env
else
  echo "Error: .env file not found in the parent directory (fpl-mcp-server/)."
  echo "Please create a .env file from the .env.example template."
  exit 1
fi

# Validate that necessary variables are set
if [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_REGION" ] || [ -z "$AR_REPO_NAME" ] || [ -z "$SERVICE_ACCOUNT_NAME" ] || [ -z "$DEPLOYING_USER_EMAIL" ]; then
    echo "Error: One or more required variables are not set in your .env file."
    echo "Please ensure GCP_PROJECT_ID, GCP_REGION, AR_REPO_NAME, SERVICE_ACCOUNT_NAME, and DEPLOYING_USER_EMAIL are set."
    exit 1
fi

# --- Derived Variables (do not change) ---
SERVICE_ACCOUNT_FULL_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# --- Script Logic ---
echo "--- Setting Google Cloud Project to ${GCP_PROJECT_ID} ---"
gcloud config set project $GCP_PROJECT_ID

echo "--- Enabling necessary Google Cloud APIs ---"
gcloud services enable \
  iam.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com

echo "--- Creating Artifact Registry repository (if it doesn't exist) ---"
gcloud artifacts repositories create $AR_REPO_NAME \
  --repository-format=docker \
  --location=$GCP_REGION \
  --description="Repository for FPL MCP Server images" --quiet || echo "Repository '$AR_REPO_NAME' already exists."

echo "--- Creating Service Account for Cloud Run (if it doesn't exist) ---"
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="FPL MCP Server Cloud Run Account" --quiet || echo "Service Account '$SERVICE_ACCOUNT_NAME' already exists."

echo "--- Granting required IAM permissions to the Service Account [${SERVICE_ACCOUNT_FULL_EMAIL}] ---"
# Grant permission to access Firestore
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_FULL_EMAIL}" \
  --role="roles/datastore.user" --quiet

# Grant permission to call AI Platform (for Gemini, etc.) if needed by the app
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_FULL_EMAIL}" \
  --role="roles/aiplatform.user" --quiet

echo "--- Granting Deploying User [${DEPLOYING_USER_EMAIL}] required deployment permissions ---"
# Grant the deploying user permission to act as the Cloud Run service account
gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT_FULL_EMAIL \
  --member="user:${DEPLOYING_USER_EMAIL}" \
  --role="roles/iam.serviceAccountUser" --quiet

# Grant the deploying user permission to deploy and manage Cloud Run services
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:${DEPLOYING_USER_EMAIL}" \
  --role="roles/run.admin" --quiet

echo "--- GCP Setup Complete ---"
echo "Project ready for deployment. You can now run deploy.sh"