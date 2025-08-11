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
This module defines the tools available to the FPL agent.

These tools interact with a backend FPL API server to fetch data about players,
teams, fixtures, and league standings. It also includes a tool for team 
optimization using PuLP and a Google Search tool for general queries.

Key Functions:
- get_top_performers: Fetches the top-performing players.
- search_players: Searches for players based on various criteria.
- get_fixtures: Retrieves match fixtures for a given gameweek.
- search_teams: Searches for teams or lists all teams.
- get_league_standings: Gets the current league table.
- get_current_gameweek: Finds the current active gameweek.
- get_optimized_fpl_team: Suggests an optimized FPL team based on constraints.
- google_search_tool: A sub-agent for performing Google searches.
"""

import os
import json
import logging
import requests
from typing import Optional, List
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone

import pulp
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODEL_NAME = os.getenv("ROOT_AGENT_MODEL", "gemini-1.5-flash")

# A sub-agent that specializes in using Google Search.
search_sub_agent = Agent(
    name="google_search",
    model=MODEL_NAME,
    instruction="You are a search specialist. Your only task is to use Google Search to answer the user's query.",
    tools=[google_search]
)

# An AgentTool that wraps the search sub-agent, making it available to the main agent.
google_search_tool = AgentTool(
    agent=search_sub_agent
)

def _get_authenticated_headers():
    """
    Constructs authentication headers for making requests to the MCP server.

    This function retrieves the server URL and API key from environment variables.
    It attempts to generate a Google-signed ID token for authentication.

    Returns:
        A tuple containing the headers dictionary and the base API URL.

    Raises:
        ValueError: If the required environment variables are not set.
    """
    mcp_server_url_from_env = os.getenv("MCP_SERVER_URL")
    api_key = os.getenv("MCP_API_KEY")

    if not mcp_server_url_from_env or not api_key:
        raise ValueError("MCP_SERVER_URL and MCP_API_KEY environment variables must be set.")

    parsed_url = urlparse(mcp_server_url_from_env)
    base_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
    api_base_url = f"{base_url}/api/v1"

    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    try:
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, base_url)
        headers["Authorization"] = f"Bearer {id_token}"
        logging.info("Successfully generated Google-signed ID token for API requests.")
    except Exception as e:
        logging.warning("Could not generate Google-signed ID token: %s. Proceeding with API key only.", e)

    return headers, api_base_url

def get_top_performers() -> str:
    """
    Retrieves the top 10 performing FPL players based on total points.

    Returns:
        A JSON string representing a list of the top 10 players.
    """
    try:
        headers, mcp_server_url = _get_authenticated_headers()
        api_url = f"{mcp_server_url}/players/"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        all_players = response.json()
        top_10_performers = sorted(
            all_players,
            key=lambda p: p.get('total_points', 0),
            reverse=True
        )[:10]
        
        return json.dumps(top_10_performers, indent=2)
        
    except Exception as e:
        logging.error("Error getting top performers: %s", e)
        return json.dumps({"error": f"An error occurred while getting top performers: {e}"})

def search_players(
    name: Optional[str] = None,
    team: Optional[str] = None,
    position: Optional[str] = None,
    filters: Optional[List[str]] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = 10
) -> str:
    """
    Searches for FPL players using a flexible set of filters and sorting options.
    Use the 'get_schema(schema_name='player')' tool first to see all available
    fields for filtering and sorting. Filters must be in the format 'field:operator:value'.
    """
    params = {
        'name': name,
        'team': team,
        'position': position,
        'filters': filters,
        'sort_by': sort_by,
        'limit': limit
    }
    # Filter out None values so they aren't sent as empty query parameters
    query_params = {k: v for k, v in params.items() if v is not None}

    if not query_params:
        return json.dumps({"error": "You must provide at least one search criteria."})
    try:
        headers, mcp_server_url = _get_authenticated_headers()
        api_url = f"{mcp_server_url}/players/search/"
        response = requests.get(api_url, params=query_params, headers=headers)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except Exception as e:
        logging.error("Error searching for players: %s", e)
        return json.dumps({"error": f"An error occurred while searching for players: {e}"})

def get_fixtures(gameweek: Optional[int] = None) -> str:
    """
    Retrieves FPL fixtures for a specific gameweek or the upcoming weeks.
    Args:
        gameweek: The gameweek number. If None, fetches for the current and next two gameweeks.
    Returns:
        A JSON string of the fixtures.
    """
    try:
        headers, mcp_server_url = _get_authenticated_headers()
        # 1. Get all teams to map IDs to names
        teams_response = requests.get(f"{mcp_server_url}/teams/", headers=headers)
        teams_response.raise_for_status()
        teams_data = teams_response.json()
        team_map = {team['id']: team['name'] for team in teams_data}
        
        gameweeks_to_fetch = []
        if gameweek is not None:
            gameweeks_to_fetch.append(gameweek)
        else:
            current_gw_str = get_current_gameweek()
            current_gw_data = json.loads(current_gw_str)
            current_gw_num = current_gw_data.get("current_gameweek")

            if not isinstance(current_gw_num, int):
                return json.dumps({"error": "Failed to determine the current gameweek."})
            
            gameweeks_to_fetch = [current_gw_num, current_gw_num + 1, current_gw_num + 2]

        all_fixtures_processed = []
        for gw in gameweeks_to_fetch:
            api_url = f"{mcp_server_url}/fixtures/"
            params = {"gameweek": gw}
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            for fixture in response.json():
                try:
                    kickoff_dt = datetime.fromisoformat(fixture['kickoff_time'].replace('Z', '+00:00'))
                    formatted_time = kickoff_dt.strftime("%A, %b %d at %I:%M %p %Z")
                except:
                    formatted_time = "Date TBC"
                all_fixtures_processed.append(
                    {
                        "gameweek": fixture.get('event'),
                        "formatted_kickoff": formatted_time,
                        "home_team": team_map.get(fixture.get('team_h'), "Unknown"),
                        "away_team": team_map.get(fixture.get('team_a'), "Unknown"),
                        "home_team_difficulty": fixture.get('team_h_difficulty'),
                        "away_team_difficulty": fixture.get('team_a_difficulty')
                    }
                )
                    
        return json.dumps(all_fixtures_processed, indent=2)

    except Exception as e:
        logging.error("Error fetching fixtures: %s", e)
        return json.dumps({"error": f"An error occurred while fetching fixtures: {e}"})

def search_teams(name: str = "") -> str:
    """
    Searches for a specific FPL team by name or lists all teams.

    Args:
        name: The name of the team. If empty, all teams are returned.

    Returns:
        A JSON string of the matching team(s).
    """
    try:
        headers, api_base_url = _get_authenticated_headers()
        if name:
            api_url = f"{api_base_url}/teams/search/"
            params = {"name": name}
            response = requests.get(api_url, headers=headers, params=params)
        else:
            api_url = f"{api_base_url}/teams/"
            response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except Exception as e:
        logging.error("Error searching for teams: %s", e)
        return json.dumps({"error": f"An error occurred while searching for teams: {e}"})

def get_league_standings() -> str:
    """
    Retrieves the current FPL league standings.

    Returns:
        A JSON string of the league standings.
    """
    try:
        headers, api_base_url = _get_authenticated_headers()
        api_url = f"{api_base_url}/standings/league"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except Exception as e:
        logging.error("Error fetching league standings: %s", e)
        return json.dumps({"error": f"An error occurred while fetching league standings: {e}"})

def get_current_gameweek() -> str:
    """
    Retrieves the current active FPL gameweek number.

    Returns:
        A JSON string containing the current gameweek number.
    """
    try:
        headers, api_base_url = _get_authenticated_headers()
        api_url = f"{api_base_url}/gameweeks/current"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()        
        return json.dumps(response.json())

    except Exception as e:
        logging.error("Error getting current gameweek: %s", e)
        return json.dumps({"error": f"An error occurred: {e}"})

def get_optimized_fpl_team(formation: str = "4-4-2", budget: int = 100) -> str:
    """
    Selects an optimized FPL team based on player form, cost, and formation.

    Args:
        formation: The desired team formation (e.g., "4-4-2").
        budget: The total budget in millions (e.g., 100).

    Returns:
        A JSON string of the optimized team.
    """
    try:
        headers, api_base_url = _get_authenticated_headers()
        players_url = f"{api_base_url}/players/"
        response = requests.get(players_url, headers=headers)
        response.raise_for_status()
        players = response.json()
        
        players = [p for p in players if p.get('status') == 'a' and p.get('form') and p.get('cost')]

        prob = pulp.LpProblem("FPL_Team_Selection", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("player", [p['id'] for p in players], cat='Binary')

        prob += pulp.lpSum([float(p['form']) * player_vars[p['id']] for p in players])
        prob += pulp.lpSum([p['cost'] * player_vars[p['id']] for p in players]) <= budget * 10 # Budget is in millions

        formation_map = {
            "4-4-2": {"Goalkeeper": 1, "Defender": 4, "Midfielder": 4, "Forward": 2},
            "4-5-1": {"Goalkeeper": 1, "Defender": 4, "Midfielder": 5, "Forward": 1},
            "3-5-2": {"Goalkeeper": 1, "Defender": 3, "Midfielder": 5, "Forward": 2},
            "3-4-3": {"Goalkeeper": 1, "Defender": 3, "Midfielder": 4, "Forward": 3},
            "4-3-3": {"Goalkeeper": 1, "Defender": 4, "Midfielder": 3, "Forward": 3},
        }
        
        squad_size = 11
        if formation not in formation_map:
            return json.dumps({"error": f"Formation {formation} not supported. Please choose from {list(formation_map.keys())}"})
            
        prob += pulp.lpSum([player_vars[p['id']] for p in players]) == squad_size
        for pos, count in formation_map[formation].items():
             prob += pulp.lpSum([player_vars[p['id']] for p in players if p['position'] == pos]) == count

        team_ids = set(p['team'] for p in players)
        for team_id in team_ids:
            prob += pulp.lpSum([player_vars[p['id']] for p in players if p['team'] == team_id]) <= 3

        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if pulp.LpStatus[prob.status] != 'Optimal':
            return json.dumps({"error": "Could not find an optimal team for the given budget and formation."})

        selected_players_output = {
            "formation": formation,
            "Goalkeepers": [], "Defenders": [], "Midfielders": [], "Forwards": []
        }
        total_cost = 0
        for p in players:
            if player_vars[p['id']].varValue == 1:
                position_key = p['position'] + 's'
                if position_key in selected_players_output:
                    selected_players_output[position_key].append(f"{p['web_name']} ({p['cost']/10.0}m)")
                    total_cost += p['cost']
        
        selected_players_output["total_cost"] = f"£{total_cost/10.0:.1f}m"
        selected_players_output["status"] = "Team selected successfully"
        
        return json.dumps(selected_players_output, indent=2)

    except Exception as e:
        logging.error("Error optimizing team: %s", e)
        return json.dumps({"error": f"An error occurred while optimizing the team: {e}"})
    
def get_schema(schema_name: str) -> str:
    """Retrieves the available fields and their data types for a given schema
    (e.g., 'player', 'team'). This is essential for constructing valid filters
    for the various search tools.
    """
    if not schema_name:
        return json.dumps({"error": "No schema name provided."})
    try:
        headers, mcp_server_url = _get_authenticated_headers()
        api_url = f"{mcp_server_url}/schemas/{schema_name}"
        response = requests.get(api_url,headers=headers)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except Exception as e:
        logging.error("Error getting schema: %s", e)
        return json.dumps({"error": f"An error occurred while getting schema: {e}"})

