#app/api/v1/endpoint.py
from fastapi import APIRouter, HTTPException, Query, Depends, status
from app.services.fpl_sync import sync_all_fpl_data
from fastapi.security.api_key import APIKeyHeader # For API Key authentication (recommended)
from app.core.config import get_settings
from typing import List, Optional, Dict, Any
from app.crud import crud_fpl
from app.schemas import fpl_schemas
from starlette.concurrency import run_in_threadpool

settings = get_settings()


router = APIRouter()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != settings.SYNC_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate API Key")
    return api_key



@router.get("/players/{player_id}", response_model=fpl_schemas.Player, tags=["Players"])
def read_player(player_id: int):
    player = crud_fpl.get_player_by_id(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.get("/players/", response_model=List[fpl_schemas.Player], tags=["Players"])
def read_players(
    max_cost: Optional[int] = Query(None, description="Filter players by maximum cost"),
    position: Optional[str] = Query(None, description="Filter players by position (element_type)"),
):
    players = crud_fpl.get_all_players()
    if max_cost:
        players = [player for player in players if player.cost <= max_cost]
    if position:
        players = [player for player in players if player.position == position]
    return players

@router.get("/teams/{team_id}", response_model=fpl_schemas.Team, tags=["Teams"])
def read_team(team_id: int):
    team = crud_fpl.get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.get("/teams/", response_model=List[fpl_schemas.Team], tags=["Teams"])
def read_teams():
    teams = crud_fpl.get_all_teams()
    return teams

@router.get("/fixtures/", response_model=List[fpl_schemas.Fixture], tags=["Fixtures"])
def read_fixtures(gameweek :Optional[int]= Query(None, description="Filter fixtures by gameweek")):
    fixtures_data = crud_fpl.get_all_from_collection("fixtures")
    fixtures = [fpl_schemas.Fixture(**f) for f in fixtures_data]
    
    current_gameweek = gameweek or crud_fpl.get_current_gameweek()
    target_gameweek = gameweek if gameweek is not None else current_gameweek
    
    if target_gameweek is not None:
        fixtures = [fixture for fixture in fixtures if fixture.event == target_gameweek]
    return fixtures

@router.get("/gameweeks/", response_model=List[fpl_schemas.Gameweek], tags=["Gameweeks"])
def read_gameweeks():
    gameweeks = crud_fpl.get_all_gameweeks()
    return gameweeks


@router.get("/standings/league", response_model=List[fpl_schemas.Standing], tags=["Standings"])
def read_league_standings():
    standings = crud_fpl.get_all_from_collection("league_standings")
    if not standings:
        raise  HTTPException(status_code=404, detail="League standings not found. Please run a data sync.")
    
    return sorted(standings, key=lambda x: x.get('position', 99))


    

@router.get("/mcp/player-context/{player_id}", response_model=fpl_schemas.PlayerContext, tags=["MCP"])
def read_player_context(player_id: int):
    """
    MCP Endpoint: Retrieves a rich, contextualized document for a single player,
    optimized for consumption by an AI agent.
    """
    player_data = crud_fpl.get_player_by_id(player_id)
    if not player_data:
        raise HTTPException(status_code=404, detail="Player not found")

    context = fpl_schemas.PlayerContext(**player_data)

    team_id = player_data.get("team")
    if team_id:
        team_data = crud_fpl.get_team_by_id(team_id)
        if team_data:
            context.team_details = fpl_schemas.Team(**team_data)

    # Fetch and attach upcoming fixtures for the player's team
    all_fixtures_data = crud_fpl.get_all_from_collection("fixtures") 
    all_fixtures_models = [fpl_schemas.Fixture(**f) for f in all_fixtures_data]
    
    
    player_team_id = player_data.get("team")
    upcoming_fixtures = [
        f for f in all_fixtures_models 
        if (f.team_h == player_team_id or f.team_a == player_team_id) and not f.finished and (f.event is None or f.event >= crud_fpl.get_current_gameweek()) 
    ]
    context.upcoming_fixtures = sorted(upcoming_fixtures, key=lambda x: x.get('kickoff_time'))[:5] # Get next 5

    return context


# --- New Sync Endpoint ---
@router.post("/sync", summary="Trigger FPL data synchronization", tags=["Admin"], status_code=status.HTTP_200_OK)
async def sync_data(api_key: str = Depends(get_api_key)): # Add Depends(get_api_key) for authentication
    """
    Triggers the full FPL data synchronization from API to Firestore.
    Requires an API key in the 'X-API-Key' header.
    """
    try:
        # It's better to run sync_all_fpl_data in a background task to avoid timeout issues
        # with long-running sync operations on Cloud Run.
        # However, for simplicity and direct testing, calling it directly is fine for now.
        # If sync_all_fpl_data itself makes I/O calls, it might need to be awaited
        # if it's an async function, or run in a thread pool if it's sync blocking.
        # Since sync_all_fpl_data is likely blocking I/O, it's best to run it in a threadpool.
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(sync_all_fpl_data)

        return {"message": "FPL data synchronization started. Check logs for progress."}
    except Exception as e:
        print(f"Error during FPL data synchronization: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to trigger sync: {e}")