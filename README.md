# FPL Model Context Protocol (MCP) Application

## Empowering AI with Real-time FPL Insights

This repository presents a robust, full-stack application designed to bridge the gap between dynamic Fantasy Premier League (FPL) data and intelligent AI agents. By leveraging Google Cloud services, it provides a scalable and efficient solution for delivering contextualized FPL information, enabling AI to offer insightful analysis and recommendations.

The project is structured into three core components:

1.  **FPL Model Context Protocol (MCP) Server:** The data backbone, responsible for ingesting, processing, and serving FPL data.
2.  **FPL Agent:** An intelligent AI agent powered by Vertex AI Agent Engine, capable of understanding FPL queries and utilizing tools to provide answers.
3.  **Frontend:** A user-friendly web interface for seamless interaction with the FPL Agent.
4.  **FPL Backend:** A Flask application acting as a proxy between the Frontend and the Vertex AI Agent Engine.

## Project Structure

-   `fpl-mcp-server/`: Contains the FastAPI application for FPL data management and serving.
-   `fpl-agent/`: Houses the Vertex AI Agent Engine agent definition and related tools.
-   `frontend/`: The React-based web application for user interaction.
-   `fpl-backend/`: The Flask proxy server for the Vertex AI Agent Engine.

## 1. FPL Model Context Protocol (MCP) Server

The FPL MCP Server is a high-performance FastAPI application designed to be the authoritative source of FPL data for AI agents. It meticulously fetches, transforms, and stores FPL data, making it readily accessible and contextually rich.

**Key Capabilities:**

*   **Real-time Data Synchronization:** Continuously pulls the latest FPL data from the official API, ensuring agents always have up-to-date information.
*   **Robust Data Storage:** Persists FPL data (players, teams, fixtures, gameweeks, league standings) in Google Cloud Firestore, offering a flexible and scalable NoSQL database solution.
*   **Comprehensive API Endpoints:** Exposes a well-defined set of RESTful API endpoints for programmatic access to all FPL data entities.
*   **AI-Optimized Context:** Features a specialized `/mcp/player-context/{player_id}` endpoint that delivers deeply contextualized player information, specifically structured for optimal consumption by AI models.
*   **Secure Administration:** Administrative endpoints, such as data synchronization triggers, are secured using API key authentication.

### Deploying the MCP Server to Google Cloud Run

Deploying the FPL MCP Server to Cloud Run provides a fully managed, scalable, and cost-effective solution for hosting your FPL data API.

**Prerequisites:**

*   **Google Cloud Project:** An active GCP project with billing enabled.
*   **Google Cloud SDK (`gcloud`):** Installed and authenticated to your GCP project.
*   **Firestore:** Enabled in your GCP project. The server will automatically connect to it.
*   **Artifact Registry:** Enabled in your GCP project for Docker image storage.

**Deployment Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/fpl-mcp-adk.git
    cd fpl-mcp-adk
    ```

2.  **Navigate to the Server Directory:**
    ```bash
    cd fpl-mcp-server
    ```

3.  **Configure Environment Variables for Deployment:**
    Create a `.env` file in the `fpl-mcp-server/` directory. **Crucially, this file should NOT be committed to Git.**

    ```ini
    # fpl-mcp-server/.env
    GCP_PROJECT_ID="your-gcp-project-id"
    GCP_REGION="your-gcp-region" # e.g., us-central1
    AR_REPO_NAME="fpl-mcp-repo" # Artifact Registry repository name
    SERVICE_ACCOUNT_NAME="fpl-mcp-server-sa" # Name for the Cloud Run service account
    DEPLOYING_USER_EMAIL="your-gcp-user-email" # Your email for IAM permissions
    FPL_API_BASE_URL="https://fantasy.premierleague.com/api"
    SYNC_INTERVAL_HOURS=2
    SYNC_SECRET="your-strong-secret-api-key-for-sync"
    ```
    *   Replace placeholders with your actual GCP project ID, desired region, and email.
    *   `AR_REPO_NAME` is the name of the Artifact Registry repository where your Docker image will be stored.
    *   `SERVICE_ACCOUNT_NAME` is the name for the dedicated service account Cloud Run will use.
    *   `SYNC_SECRET` should be a strong, randomly generated key.

4.  **Set up GCP Project and Services:**
    Run the setup script to enable necessary APIs, create an Artifact Registry repository, and configure IAM permissions.
    ```bash
    chmod +x setup_gcp_project.sh
    ./setup_gcp_project.sh
    ```

5.  **Build and Deploy to Cloud Run:**
    This script will build the Docker image and deploy it to Cloud Run.
    ```bash
    chmod +x deployment/deploy.sh
    ./deployment/deploy.sh
    ```
    Upon successful deployment, the script will output the URL of your deployed Cloud Run service. Make a note of this URL.

6.  **Run Initial Data Synchronization (Optional but Recommended):**
    Once the server is deployed and running, you can trigger an initial data sync to populate your Firestore database. Replace `YOUR_CLOUD_RUN_URL` with the URL from the previous step and `YOUR_SYNC_SECRET` with the value from your `.env` file.
    ```bash
    curl -X POST "YOUR_CLOUD_RUN_URL/sync" -H "X-API-Key: YOUR_SYNC_SECRET"
    ```

## 2. FPL Agent

The FPL Agent is the intelligent core of this application, built upon the powerful Vertex AI Agent Engine. It acts as a sophisticated conversational AI, capable of understanding complex FPL-related queries and providing accurate, data-driven responses.

**Core Intelligence:**

*   **Natural Language Understanding (NLU):** Processes and interprets user queries, extracting intent and key entities related to FPL.
*   **Advanced Tool Utilization:** Dynamically selects and executes the most appropriate tools (e.g., `get_top_performers`, `search_players`, `get_fixtures`, `get_optimized_fpl_team`) to retrieve specific FPL data from the deployed MCP Server.
*   **Contextual Reasoning:** Synthesizes information from various data sources and tool outputs to generate coherent and highly relevant responses.
*   **Strategic Google Search Fallback:** When FPL-specific tools cannot provide the answer (e.g., for breaking news, transfer rumors), the agent intelligently resorts to Google Search for real-time, qualitative information.

### Deploying the FPL Agent to Vertex AI Agent Engine

**Prerequisites:**

*   **Deployed MCP Server:** The FPL MCP Server must be deployed and accessible via a public URL.
*   **Google Cloud Project:** Same GCP project as the MCP Server.
*   **Vertex AI API:** Enabled in your GCP project.

**Deployment Steps:**

1.  **Navigate to the Agent Directory:**
    ```bash
    cd fpl-agent
    ```

2.  **Configure Environment Variables for Agent Deployment:**
    Create a `.env` file in the `fpl-agent/` directory. **Do NOT commit this file to Git.**

    ```ini
    # fpl-agent/.env
    GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    GOOGLE_CLOUD_LOCATION="your-gcp-region" # Must match MCP Server region
    GOOGLE_CLOUD_STORAGE_BUCKET="your-adk-staging-bucket" # e.g., your-gcp-project-id-adk-staging
    ROOT_AGENT_MODEL="gemini-1.5-flash" # Or other suitable Gemini model
    MCP_SERVER_URL="YOUR_CLOUD_RUN_MCP_SERVER_URL" # The URL from MCP Server deployment
    MCP_API_KEY="YOUR_SYNC_SECRET" # The SYNC_SECRET from MCP Server .env
    FPL_TEAM_ID="your-fpl-team-id" # Optional: Your FPL team ID if needed by agent logic
    ```
    *   `GOOGLE_CLOUD_STORAGE_BUCKET` should be a unique GCS bucket for Agent Engine staging artifacts.
    *   `MCP_SERVER_URL` is the public URL of your deployed FPL MCP Server.
    *   `MCP_API_KEY` is the `SYNC_SECRET` you defined for your MCP Server.

3.  **Install Poetry Dependencies and Build Wheel:**
    ```bash
    poetry install
    poetry build --format=wheel --output=deployment
    ```

4.  **Deploy the Agent:**
    ```bash
    python deployment/deploy.py --create
    ```
    This script will package your agent and deploy it to Vertex AI Agent Engine. Upon successful deployment, it will output the `resource_id` of your deployed agent. Make a note of this ID.

## 3. Frontend

The Frontend provides an intuitive and engaging user experience for interacting with the FPL Agent. Built with React, it offers a dynamic chat interface where users can pose FPL-related questions and receive intelligent responses.

**User Experience Highlights:**

*   **Interactive Chat Interface:** A modern, responsive chat UI for seamless conversations.
*   **Real-time Responses:** Displays agent responses as they are generated, providing an immediate feedback loop.
*   **Clear Presentation:** Formats FPL data (e.g., player lists, team standings) in easily digestible tables and cards.

### Running the Frontend Locally

**Prerequisites:**

*   Node.js (LTS version recommended)
*   npm or yarn

**Setup Steps:**

1.  **Navigate to the Frontend Directory:**
    ```bash
    cd frontend
    ```

2.  **Install Dependencies:**
    ```bash
    npm install
    # or yarn install
    ```

3.  **Configure Backend API Endpoint:**
    Create a `.env.local` file in the `frontend/` directory. **Do NOT commit this file to Git.**

    ```ini
    # frontend/.env.local
    VITE_BACKEND_API_URL="http://localhost:5001" # Or the URL of your deployed fpl-backend
    ```
    *   If you are running the `fpl-backend` locally, use `http://localhost:5001`.
    *   If you deploy the `fpl-backend` to Cloud Run, use its public URL here.

4.  **Start the Development Server:**
    ```bash
    npm run dev
    # or yarn dev
    ```
    The frontend application will typically be available at `http://localhost:5173` (or another port if 5173 is in use).

## 4. FPL Backend (Flask Proxy)

The `fpl-backend` is a lightweight Flask application that serves as an intermediary between the `frontend` and the deployed Vertex AI Agent Engine. It handles API requests from the frontend, forwards them to the Agent Engine, and streams back the responses.

**Role in the Architecture:**

*   **API Proxy:** Simplifies communication between the frontend (which might not directly call Vertex AI APIs) and the Agent Engine.
*   **Session Management:** Manages session creation and message posting to the Agent Engine.
*   **Security Layer:** Can be extended to add additional authentication/authorization layers before reaching the Agent Engine.

### Deploying the FPL Backend to Google Cloud Run

**Prerequisites:**

*   **Deployed FPL Agent:** The FPL Agent must be deployed and its `resource_id` noted.
*   **Google Cloud Project:** Same GCP project as other components.

**Deployment Steps:**

1.  **Navigate to the Backend Directory:**
    ```bash
    cd fpl-backend
    ```

2.  **Configure Environment Variables for Backend Deployment:**
    Create a `.env` file in the `fpl-backend/` directory. **Do NOT commit this file to Git.**

    ```ini
    # fpl-backend/.env
    PROJECT_ID="your-gcp-project-id"
    LOCATION="your-gcp-region" # Must match Agent Engine region
    AGENT_ENGINE_ID="YOUR_FPL_AGENT_RESOURCE_ID" # The resource_id from FPL Agent deployment
    ```

3.  **Build and Deploy to Cloud Run:**
    This process is similar to the MCP Server. You'll need a `Dockerfile` and a deployment script (which you might need to create if not already present, similar to `fpl-mcp-server/deployment/deploy.sh`).

    *Example `Dockerfile` (in `fpl-backend/Dockerfile`):*
    ```dockerfile
    # Use an official Python runtime as a parent image
    FROM python:3.9-slim-buster

    # Set the working directory in the container
    WORKDIR /app

    # Copy the current directory contents into the container at /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    COPY . .

    # Expose the port the app runs on
    EXPOSE 5001

    # Run the application
    CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
    ```

    *Example Deployment (assuming you create `fpl-backend/deployment/deploy.sh`):*
    ```bash
    # fpl-backend/deployment/deploy.sh
    #!/bin/bash
    set -e

    if [ -f ../.env ]; then
      source ../.env
    else
      echo "Error: .env file not found in the parent directory (fpl-backend/)."
      exit 1
    fi

    IMAGE_NAME="gcr.io/${PROJECT_ID}/fpl-backend"
    SERVICE_NAME="fpl-backend-service"

    echo "Building Docker image..."
    docker build -t ${IMAGE_NAME} .
    docker push ${IMAGE_NAME}

    echo "Deploying to Cloud Run..."
    gcloud run deploy ${SERVICE_NAME} \
      --image ${IMAGE_NAME} \
      --platform managed \
      --region ${LOCATION} \
      --allow-unauthenticated \
      --set-env-vars=PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION},AGENT_ENGINE_ID=${AGENT_ENGINE_ID} \
      --port 5001 \
      --no-cpu-throttling \
      --min-instances 1 \
      --max-instances 1 \
      --memory 512Mi \
      --timeout 300 \
      --ingress all \
      --project ${PROJECT_ID}

    echo "Deployment complete. Service URL: $(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${LOCATION} --format='value(status.url)')"
    ```

    Then run:
    ```bash
    chmod +x deployment/deploy.sh
    ./deployment/deploy.sh
    ```
    Make a note of the deployed URL for the `fpl-backend` service.

## Contributing

We welcome contributions to this project! Please see `CONTRIBUTING.md` (if available) for guidelines.

## License

This project is licensed under the Apache License, Version 2.0 - see the `LICENSE` file for details.