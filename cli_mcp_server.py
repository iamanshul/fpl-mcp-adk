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
This script provides a command-line interface for the FPL agent.

It uses the Model-Context-Protocol (MCP) server to expose the agent's tools
over standard input/output, allowing it to be used in a local CLI environment.
"""

import asyncio
from model_context_protocol.server.mcp import McpServer
from model_context_protocol.server.stdio import StdioServerTransport

# VERIFIED: Import the simple tool functions directly.
from fpl_agent.tools.fpl_tools import (
    get_top_performers,
    search_players,
    get_fixtures,
    search_teams,
    get_league_standings,
    get_current_gameweek,
    get_optimized_fpl_team
)

async def main():
    server = McpServer(
        name="fpl-cli-server",
        version="1.0.0",
    )

    # VERIFIED: Register ONLY the simple Python functions.
    # The MCP server can handle these directly.
    server.register_tool("get_top_performers", get_top_performers)
    server.register_tool("search_players", search_players)
    server.register_tool("get_fixtures", get_fixtures)
    server.register_tool("search_teams", search_teams)
    server.register_tool("get_league_standings", get_league_standings)
    server.register_tool("get_current_gameweek", get_current_gameweek)
    server.register_tool("get_optimized_fpl_team", get_optimized_fpl_team)
    
    # NOTE: We are NOT registering the 'Google Search_tool' because it is a
    # complex AgentTool object, which this simple server cannot handle.
    # The main Gemini CLI often has its own built-in web search capabilities.

    print("FPL MCP Server is running. Waiting for Gemini CLI to connect...")

    transport = StdioServerTransport()
    await server.connect(transport)

if __name__ == "__main__":
    asyncio.run(main())