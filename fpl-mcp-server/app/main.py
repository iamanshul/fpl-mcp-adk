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
This is the main entry point for the FPL MCP FastAPI application.

It sets up the FastAPI app, includes the API routers, and defines the root
and task-triggering endpoints.
"""

from fastapi import FastAPI, BackgroundTasks
from app.api.v1 import endpoints
from app.services import fpl_sync

app = FastAPI(
    title="FPL Model Context Protocol Server",
    description="An API server to provide contextualized FPL data for AI agents.",
    version="0.1.0",
)

app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/")
def read_root():
    """A simple root endpoint to confirm the server is running."""
    return {"message": "Welcome to the FPL MCP Server"}

@app.post("/tasks/sync-fpl-data")
async def trigger_fpl_sync(background_tasks: BackgroundTasks):
    """
    A secure endpoint to trigger the FPL data synchronization job.
    This endpoint is designed to be called by a trusted service like Cloud Scheduler.
    It runs the synchronization job in the background to avoid request timeouts.
    """
    background_tasks.add_task(fpl_sync.sync_all_fpl_data)
    return {
        "status": "success",
        "message": "FPL data synchronization job started in the background.",
    }