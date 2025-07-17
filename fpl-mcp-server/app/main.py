#app/main.py
from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from app.api.v1 import endpoints
from app.services import fpl_sync
from app.core.config import get_settings


app = FastAPI(
    title="FPL Model Context protocol Server",
    description="An API server to provide contextualized FPL data for AI agents.",
    version="0.1.0"
)

app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the FPL MCP Server"}

@app.post("/tasks/sync-fpl-data")
async def trigger_fpl_sync(background_tasks: BackgroundTasks):
    """
    A secure endpoint to trigger the FPL data synchronization job.
    This endpoint should only be called by a trusted service like Cloud Scheduler.
    It runs the sync job in the background to avoid request timeouts.
    """
    background_tasks.add_task(fpl_sync.sync_all_fpl_data)
    return {"status": "success", "message": "FPL data synchronization job started in the background."}
