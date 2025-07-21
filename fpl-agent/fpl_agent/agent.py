import os
from google.adk.agents import Agent
from fpl_agent.prompts import AGENT_INSTRUCTION
from fpl_agent.tools.fpl_tools import (get_all_players, get_top_performers, search_players, search_teams, google_search_tool)

root_agent = Agent(
    instruction=AGENT_INSTRUCTION,
    name="fpl_agent",
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-1.5-flash"),
    tools=[
        get_all_players,
        get_top_performers,
        search_players,
        search_teams,
        google_search_tool,
    ],
)
