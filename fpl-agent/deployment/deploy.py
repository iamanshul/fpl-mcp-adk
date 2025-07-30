# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# Author: Anshul Kapoor
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Deployment script for the Fantasy Premier League (FPL) agent to Google Cloud Vertex AI.

This script handles the creation, deletion, and management of the FPL agent 
as a Vertex AI Agent Engine. It uses the AdkApp framework for deployment.

Key Functions:
- setup_staging_bucket: Prepares a Google Cloud Storage bucket for deployment artifacts.
- create: Packages and deploys the agent to Vertex AI.
- delete: Removes a deployed agent from Vertex AI.
- main: Parses command-line arguments to orchestrate the deployment process.
"""

import logging
import os

import vertexai
from absl import app, flags
from fpl_agent.agent import root_agent
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions
from google.cloud import storage
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string(
    "bucket", None, "GCP bucket name (without gs:// prefix)."
)
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")

flags.DEFINE_bool("create", False, "Create a new agent.")
flags.DEFINE_bool("delete", False, "Delete an existing agent.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete"])

AGENT_WHL_FILE = "deployment/fpl_agent-0.1-py3-none-any.whl"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_staging_bucket(
    project_id: str, location: str, bucket_name: str
) -> str:
    """
    Checks if the staging bucket exists and creates it if it doesn't.

    Args:
        project_id: The GCP project ID.
        location: The GCP location for the bucket.
        bucket_name: The desired name for the bucket (without gs:// prefix).

    Returns:
        The full bucket path (gs://<bucket_name>).

    Raises:
        google_exceptions.GoogleCloudError: If bucket creation fails.
    """
    storage_client = storage.Client(project=project_id)
    try:
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket:
            logger.info("Staging bucket gs://%s already exists.", bucket_name)
        else:
            logger.info(
                "Staging bucket gs://%s not found. Creating...", bucket_name
            )
            new_bucket = storage_client.create_bucket(
                bucket_name, project=project_id, location=location
            )
            logger.info(
                "Successfully created staging bucket gs://%s in %s.",
                new_bucket.name,
                location,
            )
            new_bucket.iam_configuration.uniform_bucket_level_access_enabled = (
                True
            )
            new_bucket.patch()
            logger.info(
                "Enabled uniform bucket-level access for gs://%s.",
                new_bucket.name,
            )

    except google_exceptions.Forbidden as e:
        logger.error(
            "Permission denied for bucket gs://%s. Ensure the service account has 'Storage Admin' role. Error: %s",
            bucket_name,
            e,
        )
        raise
    except google_exceptions.Conflict as e:
        logger.warning(
            "Bucket gs://%s likely already exists but is owned by another project or was recently deleted. Error: %s",
            bucket_name,
            e,
        )
    except google_exceptions.ClientError as e:
        logger.error(
            "Failed to create or access bucket gs://%s. Error: %s",
            bucket_name,
            e,
        )
        raise

    return f"gs://{bucket_name}"


def create(env_vars: dict[str, str]) -> None:
    """
    Packages the agent, defines its dependencies, and deploys it to Vertex AI Agent Engines.
    """
    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=False,
    )

    if not os.path.exists(AGENT_WHL_FILE):
        logger.error("Agent wheel file not found at: %s. Please build the wheel file first.", AGENT_WHL_FILE)
        raise FileNotFoundError(f"Agent wheel file not found: {AGENT_WHL_FILE}")

    logger.info("Using agent wheel file: %s", AGENT_WHL_FILE)

    remote_agent = agent_engines.create(
        adk_app,
        requirements=[AGENT_WHL_FILE, 
                      "google-adk==1.5.0",
                      "requests",
                      "google-auth",
                      "python-dotenv",
                      "pulp"], 
        extra_packages=[AGENT_WHL_FILE],
        env_vars=env_vars
    )
    
    logger.info("Created remote agent: %s", remote_agent.resource_name)
    logger.info("Successfully created agent: %s", remote_agent.resource_name)


def delete(resource_id: str) -> None:
    """
    Deletes the specified agent from Vertex AI.
    """
    logger.info("Attempting to delete agent: %s", resource_id)
    try:
        remote_agent = agent_engines.get(resource_id)
        remote_agent.delete(force=True)
        logger.info("Successfully deleted remote agent: %s", resource_id)
    except google_exceptions.NotFound:
        logger.error("Agent with resource ID %s not found.", resource_id)
    except Exception as e:
        logger.error(
            "An error occurred while deleting agent %s: %s", resource_id, e
        )


def main(argv: list[str]) -> None:
    """
    Main execution function. Parses command-line flags and orchestrates the 
    deployment or deletion of the agent. It also handles environment variable
    loading and validation.
    """
    load_dotenv()
    env_vars = {}

    project_id = FLAGS.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = FLAGS.location or os.getenv("GOOGLE_CLOUD_LOCATION")
    default_bucket_name = f"{project_id}-adk-staging" if project_id else None
    bucket_name = FLAGS.bucket or os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET", default_bucket_name)
    
    # Environment variables for the deployed agent
    env_vars["FPL_TEAM_ID"] = os.getenv("FPL_TEAM_ID")
    env_vars["ROOT_AGENT_MODEL"] = os.getenv("ROOT_AGENT_MODEL")
    env_vars["MCP_SERVER_URL"] = os.getenv("MCP_SERVER_URL")
    env_vars["MCP_API_KEY"] = os.getenv("MCP_API_KEY")

    logger.info("Using PROJECT: %s", project_id)
    logger.info("Using LOCATION: %s", location)
    logger.info("Using BUCKET NAME: %s", bucket_name)

    # --- Input Validation ---
    if not project_id:
        logger.error("Missing required GCP Project ID. Set GOOGLE_CLOUD_PROJECT or use --project_id.")
        return
    if not location:
        logger.error("Missing required GCP Location. Set GOOGLE_CLOUD_LOCATION or use --location.")
        return
    if not bucket_name:
        logger.error("Missing required GCS Bucket Name. Set GOOGLE_CLOUD_STORAGE_BUCKET or use --bucket.")
        return
    if not FLAGS.create and not FLAGS.delete:
        logger.error("You must specify either --create or --delete flag.")
        return
    if FLAGS.delete and not FLAGS.resource_id:
        logger.error("--resource_id is required when using the --delete flag.")
        return
    # --- End Input Validation ---

    try:
        staging_bucket_uri = None
        if FLAGS.create:
            staging_bucket_uri = setup_staging_bucket(
                project_id, location, bucket_name
            )

        vertexai.init(
            project=project_id,
            location=location,
            staging_bucket=staging_bucket_uri,
        )

        if FLAGS.create:
            create(env_vars)
        elif FLAGS.delete:
            delete(FLAGS.resource_id)

    except google_exceptions.Forbidden as e:
        logger.error(
            "Permission Error: Ensure the service account/user has necessary permissions (e.g., Storage Admin, Vertex AI User). Details: %s", e
        )
    except FileNotFoundError as e:
        logger.error("File Error: %s. Ensure the agent wheel file exists in the 'deployment' directory.", e)
    except Exception as e:
        logger.exception("An unexpected error occurred in main: %s", e)


if __name__ == "__main__":
    app.run(main)