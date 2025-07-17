# FPL Agent

The FPL Agent is an intelligent assistant designed to help users get information about the Fantasy Premier League. It can provide player stats, find top performers, search for specific players or teams, and fetch the latest news.

This agent is built using the Google Agent Development Kit (ADK) and connects to a custom FPL Model Context Protocol (MCP) server for its data.

## Features

* **Player & Team Search:** Find players by name, team, or position. Look up information on specific teams.
* **Performance Metrics:** Get a list of the top-performing players based on total points.
* **Web Search:** Fetches the latest news, injury updates, and transfer rumors using a dedicated Google Search sub-agent.
* **Configurable:** The agent's model can be configured via a `.env` file.

## Project Structure
fpl-agent/
|-- deployment/
|   |-- Dockerfile
|-- eval/
|   |-- fpl_eval_set_001.evalset.json
|-- fpl_agent/
|   |-- init.py
|   |-- agent.py
|   |-- prompts.py
|   |-- tools/
|-- tests/
|   |-- test_tools.py
|-- .dockerignore
|-- .env
|-- pyproject.toml
|-- README.md


## Setup and Installation

1.  **Clone the repository** (or ensure you are in the project's root directory).
2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install dependencies in editable mode:**
    ```bash
    pip install -e ".[test]"
    ```
4.  **Create your `.env` file:**
    ```bash
    echo "ROOT_AGENT_MODEL='gemini-1.5-flash'" > .env
    ```

## Running Locally

To run the full system locally, you need three separate terminal windows.

1.  **Terminal 1: Start the Firestore Emulator**
    ```bash
    gcloud emulators firestore start --host-port=localhost:8950
    ```

2.  **Terminal 2: Start the FPL MCP Server**
    ```bash
    cd /path/to/your/fpl-mcp-server
    export FIRESTORE_EMULATOR_HOST=localhost:8950
    uvicorn app.main:app --reload
    ```

3.  **Terminal 3: Run the FPL Agent**
    * For an interactive command-line interface:
        ```bash
        cd /path/to/your/fpl-agent
        adk run fpl_agent
        ```
    * For the web interface:
        ```bash
        cd /path/to/your/fpl-agent
        adk web --port 8001
        ```

## Testing and Evaluation

* **To run unit tests:**
    ```bash
    pytest
    ```
* **To run the evaluation set:**
    ```bash
    adk eval fpl_agent eval/fpl_eval_set_001.evalset.json
    ```