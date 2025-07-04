#app/api/v1/endpoint.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.crud import crud_fpl
from app.schemas import fpl_schemas

router = APIRouter()

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
    fixtures = crud_fpl.get_all_fixtures()
    if gameweek is not None:
        fixtures = [fixture for fixture in fixtures if fixture.gameweek == gameweek]
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
    all_fixtures = crud_fpl.get_all_fixtures() # Assumes implementation
    player_team_id = player_data.get("team")
    upcoming_fixtures = [
        f for f in all_fixtures 
        if (f.get('team_h') == player_team_id or f.get('team_a') == player_team_id) and not f.get('finished')
    ]
    context.upcoming_fixtures = sorted(upcoming_fixtures, key=lambda x: x.get('kickoff_time'))[:5] # Get next 5

    return context
    
    