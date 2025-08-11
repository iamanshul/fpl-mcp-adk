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
This script provides a Flask-based backend for the FPL agent.
It handles session creation and message posting to the Vertex AI Agent Engine.
"""

import os
import traceback
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import vertexai
from vertexai.agent_engines import AgentEngine

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
PROJECT_ID = os.getenv("PROJECT_ID")
GCP_LOCATION = os.getenv("LOCATION")
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
print(f"Attempting to initialize Agent Engine with ID: {AGENT_ENGINE_ID}")

# --- INITIALIZATION ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)

remote_app = None
if all([PROJECT_ID, GCP_LOCATION, AGENT_ENGINE_ID]):
    try:
        vertexai.init(project=PROJECT_ID, location=GCP_LOCATION)
        remote_app = AgentEngine(AGENT_ENGINE_ID)
        logging.info("✅ Agent Engine initialized successfully.")
    except Exception as e:
        logging.error(f"❌ Error initializing Agent Engine: {e}")
else:
    logging.error("❌ Missing required environment variables.")

# --- API ENDPOINTS ---
@app.route('/create_session', methods=['POST', 'OPTIONS'])
def create_session_endpoint():
    """
    Creates a new session for the user with the Agent Engine.
    Handles CORS preflight requests.
    """
    if request.method == 'OPTIONS':
        return '', 204
    if not remote_app:
        return jsonify({"error": "Agent Engine not initialized"}), 500
    user_id = request.json.get('user_id', f"user-{os.urandom(8).hex()}")
    try:
        session = remote_app.create_session(user_id=user_id)
        return jsonify({"session_id": session['id']})
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/post_message', methods=['POST', 'OPTIONS'])
def post_message_endpoint():
    """
    Posts a message to the Agent Engine and returns the response.
    Handles CORS preflight requests and streams the response from the agent.
    """
    if request.method == 'OPTIONS':
        return '', 204
    if not remote_app:
        return jsonify({"error": "Agent Engine not initialized"}), 500
    
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')
    user_id = data.get('user_id')

    if not all([session_id, message, user_id]):
        return jsonify({"error": "Missing session_id, message, or user_id"}), 400

    try:
        response_stream = remote_app.stream_query(
            user_id=user_id,
            session_id=session_id,
            message=message
        )
        
        final_text_response = ""
        
        for event in response_stream:
            content = event.get("content", {})
            
            if content.get("role") == "model":
                for part in content.get("parts", []):
                    if "text" in part:
                        final_text_response += part["text"]
        
        if not final_text_response:
             final_text_response = "I was unable to generate a text response. Please try asking in a different way."

        return jsonify({"response": final_text_response})

    except Exception as e:
        logging.error(f"!!! An error occurred while querying the agent: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)