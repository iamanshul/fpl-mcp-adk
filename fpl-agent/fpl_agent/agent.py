from google.adk.agents import Agent
import os
from dotenv import load_dotenv
from fpl_agent.tools.fpl_tools import (get_all_players, get_top_performers, search_players, search_teams, google_search_tool)
from fpl_agent.prompts import AGENT_INSTRUCTION


load_dotenv()


# We name the variable 'root_agent' to exactly match the pattern in software-bug-assistant
root_agent = Agent(
    name="fpl_agent",
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=AGENT_INSTRUCTION,
    description="An agent that provides FPL player information by querying an FPL server.",
    tools=[
        get_all_players,
        get_top_performers,
        search_players,
        search_teams,
        google_search_tool,
    ],
)