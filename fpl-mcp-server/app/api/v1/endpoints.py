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
This module defines the API endpoints for the FPL MCP server.

It provides a set of RESTful endpoints to access FPL data, including players,
teams, fixtures, and league standings. It also includes administrative
endpoints for triggering data synchronization and a specialized MCP endpoint
for providing rich context to AI agents.
"""

import logging
from typing import List, Optional, Dict, Type

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.security.api_key import APIKeyHeader
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.config import get_settings
from app.crud import crud_fpl
from app.schemas import fpl_schemas
from app.services.fpl_sync import sync_all_fpl_data, _is_data_stale

settings = get_settings()

# Global lock to prevent multiple concurrent syncs
SYNC_IN_PROGRESS = False

# Dependency to check for data staleness
async def check_data_staleness(background_tasks: BackgroundTasks):
    """Dependency that checks if the FPL data is stale and triggers a background sync if needed."""
    global SYNC_IN_PROGRESS
    if SYNC_IN_PROGRESS:
        logging.info("Sync already in progress. Skipping check.")
        return

    if await run_in_threadpool(_is_data_stale, 'players'):
        logging.warning("Data is stale. Triggering background sync.")
        SYNC_IN_PROGRESS = True
        background_tasks.add_task(run_sync_with_lock)

async def run_sync_with_lock():
    """Wrapper to run the sync and ensure the lock is always released."""
    global SYNC_IN_PROGRESS
    try:
        await run_in_threadpool(sync_all_fpl_data)
    finally:
        SYNC_IN_PROGRESS = False
        logging.info("Sync finished and lock released.")

# Apply the dependency to the main router for all data-providing endpoints
router = APIRouter(dependencies=[Depends(check_data_staleness)])
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Dependency to validate the API key from the request header."""
    if api_key != settings.SYNC_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate API Key"
        )
    return api_key

# A mapping from string names to the actual Pydantic model classes
SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "player": fpl_schemas.Player,
    "team": fpl_schemas.Team,
    "fixture": fpl_schemas.Fixture,
    "gameweek": fpl_schemas.Gameweek,
    # Add any other schemas you want to make searchable here
}

@router.get("/schemas/{schema_name}", response_model=Dict[str, str], tags=["Schemas"])
def get_dynamic_schema(schema_name: str):
    """
    Returns the available fields and their data types for a given schema
    (e.g., 'player', 'team'). This allows a client to dynamically
    construct valid search queries for different data types.
    """
    schema_class = SCHEMA_MAP.get(schema_name.lower())
    if not schema_class:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found.")

    schema = schema_class.model_json_schema()
    properties = schema.get('properties', {})
    # Return a simple dictionary of field_name: field_type
    return {field: prop.get('type', 'any') for field, prop in properties.items()}


@router.get("/players/{player_id}", response_model=fpl_schemas.Player, tags=["Players"])
def read_player(player_id: int):
    """Retrieves a single player by their unique ID."""
    player = crud_fpl.get_player_by_id(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/players/", response_model=List[fpl_schemas.Player], tags=["Players"])
def read_players(
    max_cost: Optional[int] = Query(None, description="Filter players by maximum cost"),
    position: Optional[str] = Query(None, description="Filter players by position"),
):
    """Retrieves a list of all players, with optional filters."""
    players = crud_fpl.get_all_players()
    if max_cost:
        players = [p for p in players if p.cost <= max_cost]
    if position:
        players = [p for p in players if p.position == position]
    return players


@router.get("/teams/{team_id}", response_model=fpl_schemas.Team, tags=["Teams"])
def read_team(team_id: int):
    """Retrieves a single team by its unique ID."""
    team = crud_fpl.get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/teams/", response_model=List[fpl_schemas.Team], tags=["Teams"])
def read_teams():
    """Retrieves a list of all teams."""
    return crud_fpl.get_all_teams()


@router.get("/fixtures/", response_model=List[fpl_schemas.Fixture], tags=["Fixtures"])
def read_fixtures(gameweek: Optional[int] = Query(None, description="Filter fixtures by gameweek")):
    """Retrieves fixtures, optionally filtered by a specific gameweek."""
    fixtures_data = crud_fpl.get_all_from_collection("fixtures")
    fixtures = [fpl_schemas.Fixture(**f) for f in fixtures_data]

    target_gameweek = gameweek or crud_fpl.get_current_gameweek()

    if target_gameweek is not None:
        fixtures = [f for f in fixtures if f.event == target_gameweek]
    return fixtures


@router.get("/gameweeks/", response_model=List[fpl_schemas.Gameweek], tags=["Gameweeks"])
def read_gameweeks():
    """Retrieves all gameweek information."""
    return crud_fpl.get_all_gameweeks()


@router.get("/gameweeks/current", response_model=fpl_schemas.CurrentGameweek, tags=["Gameweeks"])
def read_current_gameweek():
    """Retrieves the current or next upcoming gameweek."""
    current_gameweek_id = crud_fpl.get_current_gameweek()
    if current_gameweek_id is None:
        raise HTTPException(status_code=404, detail="No current or upcoming gameweek found.")
    return fpl_schemas.CurrentGameweek(current_gameweek=current_gameweek_id)


@router.get("/standings/league", response_model=List[fpl_schemas.Standing], tags=["Standings"])
def read_league_standings():
    """Retrieves the current league standings."""
    standings = crud_fpl.get_all_from_collection("league_standings")
    if not standings:
        raise HTTPException(
            status_code=404, detail="League standings not found. Please run a data sync."
        )
    return sorted(standings, key=lambda x: x.get("position", 99))


@router.get("/mcp/player-context/{player_id}", response_model=fpl_schemas.PlayerContext, tags=["MCP"])
def read_player_context(player_id: int):
    """
    MCP Endpoint: Retrieves a rich, contextualized document for a single player.
    """
    player_data = crud_fpl.get_player_by_id(player_id)
    if not player_data:
        raise HTTPException(status_code=404, detail="Player not found")

    context = fpl_schemas.PlayerContext(**player_data)

    if team_id := player_data.get("team"):
        if team_data := crud_fpl.get_team_by_id(team_id):
            context.team_details = fpl_schemas.Team(**team_data)

    all_fixtures_data = crud_fpl.get_all_from_collection("fixtures")
    all_fixtures_models = [fpl_schemas.Fixture(**f) for f in all_fixtures_data]

    player_team_id = player_data.get("team")
    current_gameweek = crud_fpl.get_current_gameweek()
    upcoming_fixtures = [
        f
        for f in all_fixtures_models
        if (f.team_h == player_team_id or f.team_a == player_team_id)
        and not f.finished
        and (f.event is None or f.event >= current_gameweek)
    ]
    context.upcoming_fixtures = sorted(upcoming_fixtures, key=lambda x: x.kickoff_time)[:5]

    return context


@router.post("/sync", summary="Trigger FPL data synchronization", tags=["Admin"], status_code=status.HTTP_200_OK)
async def sync_data(api_key: str = Depends(get_api_key)):
    """
    Triggers the full FPL data synchronization from the FPL API to Firestore.
    This is a protected endpoint requiring a valid API key.
    """
    try:
        await run_in_threadpool(sync_all_fpl_data)
        return {"message": "FPL data synchronization started. Check logs for progress."}
    except Exception as e:
        logging.error(f"Error during FPL data synchronization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to trigger sync: {e}"
        )


@router.get("/players/search/", response_model=List[fpl_schemas.Player], tags=["Players"])
def search_players_endpoint(
    name: Optional[str] = Query(None, description="Search players by name (case-insensitive)"),
    team: Optional[str] = Query(None, description="Search players by team name (case-insensitive)"),
    position: Optional[str] = Query(None, description="Filter by position (Goalkeeper, Defender, etc.)"),
    filters: Optional[List[str]] = Query(None, description="Dynamic filters in 'field:operator:value' format. e.g., 'total_points:gt:100'"),
    sort_by: Optional[str] = Query(None, description="Field to sort results by (e.g., 'bonus', 'total_points')"),
    limit: Optional[int] = Query(10, description="Limit the number of results")
):
    """Searches for players with advanced, multiple filter criteria."""
    parsed_filters = []
    if filters:
        for f in filters:
            parts = f.split(':')
            if len(parts) == 3:
                parsed_filters.append({"field": parts[0], "operator": parts[1], "value": parts[2]})
            else:
                logging.warning(f"Ignoring malformed filter: {f}")

    players = crud_fpl.search_players(
        name=name,
        team=team,
        position=position,
        filters=parsed_filters,
        sort_by=sort_by,
        limit=limit
    )
    return players


@router.get("/teams/search/", response_model=List[fpl_schemas.Team], tags=["Teams"])
def search_teams_endpoint(
    name: str = Query(..., min_length=2, description="Search teams by name (case-insensitive)")
):
    """Searches for a team by its name."""
    teams = crud_fpl.search_teams(name=name)
    if not teams:
        raise HTTPException(status_code=404, detail="No team found matching that name")
    return teams