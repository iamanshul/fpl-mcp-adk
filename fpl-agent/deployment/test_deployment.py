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
Test script for the deployed FPL Agent on Vertex AI Agent Engine.

This script provides an interactive command-line interface to test the agent's
functionality after deployment. It handles session creation, user input, 
and streams the agent's responses, including text and tool calls.

Key Functions:
- main: Initializes the connection to the deployed agent, manages the user 
        session, and facilitates the interactive chat loop.
"""

import asyncio
import os
import logging

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from google.adk.sessions import VertexAiSessionService
from vertexai import agent_engines

FLAGS = flags.FLAGS

flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string(
    "resource_id",
    None,
    "ReasoningEngine resource ID (returned after deploying the agent)",
)
flags.DEFINE_string("user_id", None, "User ID (can be any string).")
flags.mark_flag_as_required("resource_id")
flags.mark_flag_as_required("user_id")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(argv: list[str]) -> None:
    """
    Main function to run the interactive test client for the FPL agent.
    It initializes Vertex AI, creates a session, and enters a loop to send
    user input to the agent and print the streamed responses.
    """
    load_dotenv()

    project_id = FLAGS.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = FLAGS.location or os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket or os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    if not project_id:
        logging.error("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    elif not location:
        logging.error("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    elif not bucket:
        logging.error("Missing required environment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    session_service = VertexAiSessionService(project_id, location)
    session = asyncio.run(session_service.create_session(
        app_name=FLAGS.resource_id,
        user_id=FLAGS.user_id)
    )

    agent = agent_engines.get(FLAGS.resource_id)
    logging.info(f"Found agent with resource ID: {FLAGS.resource_id}")

    logging.info(f"Created session for user ID: {FLAGS.user_id}")
    logging.info("Type 'quit' to exit.")
    while True:
        user_input = input("Input: ")
        if user_input.lower() == "quit":
            break

        for event in agent.stream_query(
            user_id=FLAGS.user_id,
            session_id=session.id,
            message=user_input
        ):
            if "content" in event:
                if "parts" in event["content"]:
                    parts = event["content"]["parts"]
                    for part in parts:
                        if "text" in part:
                            text_part = part["text"]
                            logging.info(f"Response: {text_part}")
                        elif "function_call" in part:
                            function_call = part["function_call"]
                            logging.info(f"Tool Call: {function_call['name']}({function_call['args']})")
                        elif "function_response" in part:
                            function_response = part["function_response"]
                            logging.info(f"Tool Response: {function_response['name']} -> {function_response['response']}")

    asyncio.run(session_service.delete_session(
        app_name=FLAGS.resource_id,
        user_id=FLAGS.user_id,
        session_id=session.id
    ))
    logging.info(f"Deleted session for user ID: {FLAGS.user_id}")


if __name__ == "__main__":
    app.run(main)