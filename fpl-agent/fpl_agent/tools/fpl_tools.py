import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

BASE_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000")
MODEL_NAME = os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash")

search_sub_agent = Agent(
    name="google_search",
    model=MODEL_NAME,
    instruction="You are a search specialist. Your only task is to use Google Search to answer the user's query.",
    tools = [google_search])

google_search_tool = AgentTool(
    search_sub_agent
)


def get_all_players() -> str:
    """
    Retrieves a complete list of all players from the Fantasy Premier League (FPL) server.
    Use this tool when a user asks for "all players" or "the player list".

    Returns:
        A JSON string containing the list of all players.
    """
    try:
        response = requests.get(f"{BASE_URL}/api/v1/players/")
        response.raise_for_status()  # This will raise an error for bad responses (4xx or 5xx)
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"An error occurred while fetching the player list: {e}"

def get_top_performers() -> str:
    """
    Retrieves the top 10 performing players from the FPL server by fetching all players
    and sorting them by their total points. Use this when a user asks for "top performers",
    "best players", or "who has the most points".

    Returns:
        A JSON string containing the list of the top 10 performing players.
    """
    try:
        
        response = requests.get(f"{BASE_URL}/api/v1/players/")
        response.raise_for_status()
        
        all_players = response.json()
        
        # ADDED LOGIC: Sort players by 'total_points' in descending order
        # and get the top 10.
        # This assumes players have a 'total_points' field, which is standard for FPL data.
        top_10_performers = sorted(
            all_players,
            key=lambda p: p.get('total_points', 0),
            reverse=True
        )[:10]
        
        return json.dumps(top_10_performers, indent=2)
        
    except requests.exceptions.RequestException as e:
        return f"An error occurred while fetching top performers: {e}"
    
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
    
    if not query_params:
        return "Error: You must provide at least one search criteria (name, team, or position)."
    try:
        response = requests.get(f"{BASE_URL}/api/v1/players/search/", params=query_params)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"An error occurred while searching for players: {e}"

def search_teams(name: str = "") -> str:
    """
    Searches for a specific team by its name.
    """
    try:
        response = requests.get(f"{BASE_URL}/api/v1/teams/search/", params={'name': name})
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"An error occurred while searching for teams: {e}"


    
  