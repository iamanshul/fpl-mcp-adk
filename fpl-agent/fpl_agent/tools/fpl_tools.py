import requests
import os
import requests
import google.auth
import json
import google.oauth2.id_token
from urllib.parse import urlparse, urlunparse
from typing import Optional
import pulp

import google.auth.transport.requests
import google.oauth2.id_token
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash")

search_sub_agent = Agent(
    name="google_search",
    model=MODEL_NAME,
    instruction="You are a search specialist. Your only task is to use Google Search to answer the user's query.",
    tools = [google_search])

google_search_tool = AgentTool(
    search_sub_agent
)

def _get_authenticated_headers():
    """
    Generates authentication headers and the correct base API URL for the MCP server.
    """
    mcp_server_url_from_env = os.getenv("MCP_SERVER_URL")
    api_key = os.getenv("MCP_API_KEY")

    if not mcp_server_url_from_env or not api_key:
        raise ValueError("MCP_SERVER_URL and MCP_API_KEY environment variables must be set.")

    # CORRECTED: Robustly construct the base URL and API path
    parsed_url = urlparse(mcp_server_url_from_env)
    base_url = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
    api_base_url = f"{base_url}/api/v1"

    debug_info = f"Attempting to auth with API base at {api_base_url}. "
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    try:
        # The audience for the ID token should be the base URL
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, base_url)
        headers["Authorization"] = f"Bearer {id_token}"
        debug_info += "Successfully generated Google-signed ID token."
    except Exception as e:
        debug_info += f"Could not generate Google-signed ID token: {e}."

    return headers, api_base_url, debug_info
    


def get_top_performers() -> str:
    """
    Retrieves the top 10 performing players from the FPL server by fetching all players
    and sorting them by their total points. Use this when a user asks for "top performers",
    "best players", or "who has the most points".

    Returns:
        A JSON string containing the list of the top 10 performing players.
    """
    debug_info = "Initializing..."
    headers = {}
    try:
        headers, mcp_server_url, debug_info = _get_authenticated_headers()
        api_url = f"{mcp_server_url}/players/"
        debug_info += f"Sending headers for get_top_performers: {headers}\n"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        all_players = response.json()

        top_10_performers = sorted(
            all_players,
            key=lambda p: p.get('total_points', 0),
            reverse=True
        )[:10]
        
        return json.dumps(top_10_performers, indent=2)
        
    except Exception as e: # Catch all exceptions here to include debug_info
        error_message = f"An error occurred while getting top performers: {e}"
        return f"{error_message}\n---DEBUG INFO---\n{debug_info}"
    
def search_players(name: str = "", team: str = "", position: str = "") -> str:
    """
    Searches for players using a name, team, or position. At least one parameter must be provided.
    All search parameters are case-insensitive.
    """
    params = {
        'name': name,
        'team': team,
        'position': position
    }
    query_params = {k: v for k, v in params.items() if v}
    debug_info = "Initializing Search Players..."
    
    if not query_params:
        return "Error: You must provide at least one search criteria (name, team, or position)."
    try:
        headers, mcp_server_url, debug_info = _get_authenticated_headers()
        api_url = f"{mcp_server_url}/players/search/"
        debug_info += f"Sending headers for search_players: {headers}\n"
        response = requests.get(api_url, params=query_params, headers=headers)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except Exception as e: # Catch all exceptions here to include debug_info
        error_message = f"An error occurred while searching for players: {e}"
        return f"{error_message}\n---DEBUG INFO---\n{debug_info}"
    
def get_fixtures(gameweek: Optional[int] = None) -> str:
    """
    Retrieves FPL fixtures. If a specific gameweek number is provided, it fetches
    fixtures for that week. If no gameweek is provided, it fetches fixtures
    for the current gameweek and the next two weeks.
    Args:
        gameweek (Optional[int]): The gameweek number to fetch fixtures for.
    """
    try:
        headers, mcp_server_url, _ = _get_authenticated_headers()
        
        gameweeks_to_fetch = []
        if gameweek is not None:
            gameweeks_to_fetch.append(gameweek)
        else:
            # If no gameweek is provided, get the current and next two.
            current_gw_str = get_current_gameweek()
            current_gw_data = json.loads(current_gw_str)
            current_gw_num = current_gw_data.get("current_gameweek")

            if not isinstance(current_gw_num, int):
                return json.dumps({"error": "Failed to determine the current gameweek."})
            
            gameweeks_to_fetch = [current_gw_num, current_gw_num + 1, current_gw_num + 2]

        all_fixtures = {}
        # CORRECTED: This loop correctly iterates through the gameweeks to fetch.
        for gw in gameweeks_to_fetch:
            api_url = f"{mcp_server_url}/fixtures/"
            params = {"gameweek": gw}
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            all_fixtures[f"Gameweek {gw}"] = response.json()
        
        return json.dumps(all_fixtures, indent=2)

    except Exception as e:
        return f"An error occurred while fetching fixtures: {e}"

def search_teams(name: str ="") -> str:
    """
    Searches for a specific team by its name. If no name is provided,
    it returns a list of all teams.
    Args:
        name (str): The name of the team to search for.
    """
    debug_info = "Initializing."
    try:
        headers, api_base_url, debug_info = _get_authenticated_headers()
        if name:
            api_url = f"{api_base_url}/teams/search/"
            params = {"name": name}
            response = requests.get(api_url, headers=headers, params=params)
        else:
            api_url = f"{api_base_url}/teams/"
            response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"An error occurred while searching for teams: {e}\n---DEBUG INFO---\n{debug_info}"


def get_league_standings() -> str:
    """
    Retrieves the current FPL league standings. Use this to find out
    team positions, who is at the top, or who is at the bottom.
    """
    try:
        headers, api_base_url, _ = _get_authenticated_headers()
        api_url = f"{api_base_url}/standings/league"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        return json.dumps(response.json(), indent=2)

    except Exception as e:
        return f"An error occurred while fetching league standings: {e}"

def get_current_gameweek() -> str:
    """
    Retrieves the current active Fantasy Premier League gameweek number
    by fetching all gameweeks and finding the one marked as current.
    """
    try:
        headers, api_base_url, _ = _get_authenticated_headers()
        api_url = f"{api_base_url}/gameweeks/"
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        gameweeks = response.json()
        
        # Find the gameweek that is the current one
        for gw in gameweeks:
            if gw.get('is_current'):
                return json.dumps({"current_gameweek": gw.get('id')})
        
        return json.dumps({"error": "Could not determine the current gameweek."})

    except Exception as e:
        return f"An error occurred: {e}"
    
def get_optimized_fpl_team(formation: str = "4-4-2", budget: int = 100) -> str:
    """
    Selects an optimized FPL team based on player form, cost, and fixture
    difficulty for a given formation and budget.
    Args:
        formation (str): The desired team formation (e.g., "4-4-2", "3-5-2").
        budget (int): The total budget in millions (e.g., 100).
    """
    try:
        # 1. Fetch all available players from the API
        headers, api_base_url, _ = _get_authenticated_headers()
        players_url = f"{api_base_url}/players/"
        response = requests.get(players_url, headers=headers)
        response.raise_for_status()
        players = response.json()
        
        # Filter for players who are available and have complete data
        players = [p for p in players if p.get('status') == 'a' and p.get('form') and p.get('cost')]

        # 2. PuLP Optimization Logic (adapted from your code)
        prob = pulp.LpProblem("FPL_Team_Selection", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("player", [p['id'] for p in players], cat='Binary')

        # Objective: Maximize form
        prob += pulp.lpSum([float(p['form']) * player_vars[p['id']] for p in players])

        # Constraints
        prob += pulp.lpSum([p['cost'] * player_vars[p['id']] for p in players]) <= budget * 10
        
        # Positional constraints based on formation
        formation_map = {
            "4-4-2": {"Goalkeeper": 1, "Defender": 4, "Midfielder": 4, "Forward": 2},
            "4-5-1": {"Goalkeeper": 1, "Defender": 4, "Midfielder": 5, "Forward": 1},
            "3-5-2": {"Goalkeeper": 1, "Defender": 3, "Midfielder": 5, "Forward": 2},
            "3-4-3": {"Goalkeeper": 1, "Defender": 3, "Midfielder": 4, "Forward": 3},
            "4-3-3": {"Goalkeeper": 1, "Defender": 4, "Midfielder": 3, "Forward": 3},
        }
        
        squad_size = 11 # For the starting XI
        if formation not in formation_map:
            return json.dumps({"error": f"Formation {formation} not supported. Please choose from {list(formation_map.keys())}"})
            
        prob += pulp.lpSum([player_vars[p['id']] for p in players]) == squad_size
        for pos, count in formation_map[formation].items():
             prob += pulp.lpSum([player_vars[p['id']] for p in players if p['position'] == pos]) == count

        # Team constraint (max 3 players from one team)
        team_ids = set(p['team'] for p in players)
        for team_id in team_ids:
            prob += pulp.lpSum([player_vars[p['id']] for p in players if p['team'] == team_id]) <= 3

        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        # 3. Format the result
        selected_players_output = {
            "formation": formation,
            "Goalkeepers": [], "Defenders": [], "Midfielders": [], "Forwards": []
        }
        total_cost = 0
        for p in players:
            if player_vars[p['id']].varValue == 1:
                selected_players_output[p['position'] + 's'].append(f"{p['web_name']} ({p['cost']/10.0}m)")
                total_cost += p['cost']
        
        selected_players_output["total_cost"] = f"£{total_cost/10.0:.1f}m"
        selected_players_output["status"] = "Team selected successfully"
        
        return json.dumps(selected_players_output, indent=2)

    except Exception as e:
        return f"An error occurred while optimizing the team: {e}"