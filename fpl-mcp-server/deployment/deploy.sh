#!/bin/bash
set -e
ENV_FILE_PATH="../../fpl-mcp-server/.env"

# --- Configuration is now loaded from .env file ---
# This script expects to be run from the `deployment` directory, so it looks for .env in the parent.
if [ -f "$ENV_FILE_PATH" ]; then
  # Use 'source' to load the variables into the current shell's environment.
  source "$ENV_FILE_PATH"
else
  echo "Error: .env file not found at the expected path: $ENV_FILE_PATH"
  echo "Please ensure the .env file exists in the /fpl-mcp-server/ directory."
  exit 1
fi

# --- Step 2: Validate that necessary variables are set ---
# Check each variable individually and report if not set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID is not set."
    exit 1
fi

if [ -z "$GCP_REGION" ]; then
    echo "Error: GCP_REGION is not set."
    exit 1
fi

if [ -z "$AR_REPO_NAME" ]; then
    echo "Error: AR_REPO_NAME is not set."
    exit 1
fi

if [ -z "$SERVICE_NAME" ]; then
    echo "Error: SERVICE_NAME is not set."
    exit 1
fi

if [ -z "$SERVICE_ACCOUNT_NAME" ]; then
    echo "Error: SERVICE_ACCOUNT_NAME is not set."
    exit 1
fi

if [ -z "$SYNC_SECRET" ]; then
    echo "Error: SYNC_SECRET is not set."
    exit 1
fi

# If all variables are set, you can add a success message (optional)
echo "All required variables are set."

# Validate that necessary variables are set
#if [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_REGION" ] || [ -z "$AR_REPO_NAME" ] || [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_ACCOUNT_NAME" ] || [ -z "$SYNC_SECRET" ]; then
 #   echo "Error: One or more required variables are not set in your .env file."
  #  exit 1
#fi

# --- Construct Full Resource Names ---
IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPO_NAME}/${SERVICE_NAME}:latest"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# --- Build and Push Docker Image using Cloud Build ---
echo "--- Building Docker image: ${IMAGE_TAG} ---"
# We run from the parent directory ('..') to give Cloud Build the correct context of the entire app, including the Dockerfile.
gcloud builds submit .. --tag $IMAGE_TAG --project=$GCP_PROJECT_ID

# --- Deploy to Cloud Run ---
echo "--- Deploying to Cloud Run service: ${SERVICE_NAME} ---"
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_TAG \
  --platform managed \
  --region $GCP_REGION \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 2 \
  --allow-unauthenticated \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID},FPL_API_BASE_URL=https://fantasy.premierleague.com/api,SYNC_INTERVAL_HOURS=2,SYNC_SECRET=${SYNC_SECRET}" \
  --project=$GCP_PROJECT_ID

echo "--- Deployment Complete ---"

# --- Output a helpful command for the initial data sync ---
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $GCP_REGION --format "value(status.url)" --project=$GCP_PROJECT_ID)
echo ""
echo "===================================================================================="
echo "Service deployed at: ${SERVICE_URL}"
echo ""
echo "To trigger the initial data sync, run the following command:"
echo "curl -X POST -H \"X-API-Key: ${SYNC_SECRET}\" \"${SERVICE_URL}/api/v1/sync\""
echo "===================================================================================="

