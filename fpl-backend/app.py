# fpl-backend/app.py
import os
import traceback
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

# --- INITIALIZATION ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

remote_app = None
if all([PROJECT_ID, GCP_LOCATION, AGENT_ENGINE_ID]):
    try:
        vertexai.init(project=PROJECT_ID, location=GCP_LOCATION)
        # This is the correct way to initialize from a deployed agent ID.
        remote_app = AgentEngine(AGENT_ENGINE_ID)
        print("✅ Agent Engine initialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing Agent Engine: {e}")
else:
    print("❌ Missing required environment variables.")

# --- API ENDPOINTS ---
@app.route('/create_session', methods=['POST', 'OPTIONS'])
def create_session_endpoint():
    if request.method == 'OPTIONS':
        return '', 204
    if not remote_app:
        return jsonify({"error": "Agent Engine not initialized"}), 500
    user_id = request.json.get('user_id', f"user-{os.urandom(8).hex()}")
    try:
        session = remote_app.create_session(user_id=user_id)
        return jsonify({"session_id": session['id']})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/post_message', methods=['POST', 'OPTIONS'])
def post_message_endpoint():
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
        # VERIFIED: The correct method is stream_query.
        response_stream = remote_app.stream_query(
            user_id=user_id,
            session_id=session_id,
            message=message
        )
        
        final_text_response = ""
        
        # VERIFIED: This is the correct logic to process the stream of events.
        # The agent's final answer can be split across multiple text parts.
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
        print(f"!!! An error occurred while querying the agent: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)