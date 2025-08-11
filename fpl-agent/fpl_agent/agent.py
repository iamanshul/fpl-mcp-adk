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
This script defines the core of the FPL (Fantasy Premier League) agent.

It initializes an Agent from the Google ADK library, providing it with a set of
instructions, a name, a language model, and a list of tools it can use to 
respond to user queries.
"""

import os
from google.adk.agents import Agent
from fpl_agent.prompts import AGENT_INSTRUCTION
from fpl_agent.tools.fpl_tools import (get_top_performers,
                                       search_players, 
                                       search_teams, 
                                       get_fixtures, 
                                       get_league_standings, 
                                       get_current_gameweek,
                                       google_search_tool)

# Defines the root agent for the FPL application.
# This agent is configured with specific instructions, a model, and a set of tools
# to interact with FPL data and provide assistance to the user.
root_agent = Agent(
    instruction=AGENT_INSTRUCTION,
    name="fpl_agent",
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"), # Model can be configured via environment variable
    tools=[
        get_top_performers,
        search_players,
        search_teams,
        get_fixtures,
        get_league_standings,
        get_current_gameweek,
        google_search_tool,
    ],
)