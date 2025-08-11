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
This module defines the Pydantic data models (schemas) for the FPL application.

These schemas are used for data validation, serialization, and documentation.
They represent the structure of the data used throughout the application, from
the FPL API to the Firestore database and the API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

SharedModelConfig = ConfigDict(from_attributes=True)

class Team(BaseModel):
    """Represents a single Premier League team."""
    id: int
    name: str
    short_name: str
    code: int
    strength: int
    strength_overall_home: int
    strength_overall_away: int
    strength_attack_home: int
    strength_attack_away: int
    strength_defence_home: int
    strength_defence_away: int
    pulse_id: int
    model_config = SharedModelConfig

class Player(BaseModel):
    """Represents a single FPL player."""
    id: int
    code: int
    element_type: int
    event_points: int
    first_name: str
    second_name: str
    web_name: str
    team: int
    team_code: int
    now_cost: int
    total_points: int
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    yellow_cards: int
    red_cards: int
    penalties_saved: int
    penalties_missed: int
    saves: int
    bonus: int
    bps: int
    form: str
    points_per_game: str
    selected_by_percent: str
    influence: str
    creativity: str
    threat: str
    ict_index: str
    chance_of_playing_this_round: Optional[int] = None
    chance_of_playing_next_round: Optional[int] = None
    ep_next: Optional[str] = None
    ep_this: Optional[str] = None
    news: str
    news_added: Optional[datetime] = None
    fixture_difficulty: Optional[float] = None
    recent_form: Optional[float] = None
    next_game_opponent: Optional[str] = None
    is_home: Optional[int] = None
    model_config = SharedModelConfig

    _POSITION_MAP = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}

    @computed_field
    @property
    def player_name(self) -> str:
        """Returns the full name of the player."""
        return f"{self.first_name} {self.second_name}"

    @computed_field
    @property
    def position(self) -> str:
        """Returns the player's position as a string."""
        return self._POSITION_MAP.get(self.element_type, "Unknown")

    @computed_field
    @property
    def cost(self) -> float:
        """Returns the player's cost in millions."""
        return self.now_cost / 10.0

    @computed_field
    @property
    def last_game_points(self) -> int:
        """Returns the points the player scored in the last gameweek."""
        return self.event_points

class Fixture(BaseModel):
    """Represents a single match fixture."""
    id: int
    code: int
    event: Optional[int]
    finished: bool
    kickoff_time: Optional[datetime]
    team_h: int
    team_a: int
    team_h_score: Optional[int] = None
    team_a_score: Optional[int] = None
    team_h_difficulty: int
    team_a_difficulty: int
    stats: List[Dict[str, Any]] = []
    model_config = SharedModelConfig

class GameStat(BaseModel):
    """Represents game statistics for a player in a match."""
    stat_id: Optional[int] = None
    game_id: int
    player_id: int
    goals_scored: int = 0
    assists: int = 0
    own_goals: int = 0
    penalties_saved: int = 0
    penalties_missed: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    saves: int = 0
    bonus: int = 0
    bps: int = 0
    minutes: int = 0
    model_config = SharedModelConfig

class Standing(BaseModel):
    """Represents a team's position in the league standings."""
    position: int
    team_id: int
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    model_config = SharedModelConfig

class Gameweek(BaseModel):
    """Represents a single gameweek in the FPL season."""
    id: int
    name: str
    deadline_time: datetime
    deadline_time_epoch: Optional[int] = None
    average_entry_score: int
    finished: bool
    data_checked: bool
    highest_scoring_entry: Optional[int] = None
    highest_score: Optional[int] = None
    deadline_time_game_offset: Optional[int] = None
    deadline_time_formatted: Optional[str] = None
    finished_provisional: Optional[bool] = None
    is_previous: bool
    is_current: bool
    is_next: bool
    can_enter: Optional[bool] = None
    top_element: Optional[int] = None
    top_element_info: Optional[Dict[str, Any]] = None
    transfers_made: Optional[int] = None
    chip_plays: Optional[List[Dict[str, Any]]] = None
    most_vice_captained: Optional[int] = None
    h2h_ko_matches_created: Optional[bool] = None
    release_time: Optional[datetime] = None
    cup_leagues_created: Optional[bool] = None
    most_selected: Optional[int] = None
    most_captained: Optional[int] = None
    most_transferred_in: Optional[int] = None
    overrides: Optional[Dict[str, Any]] = None
    model_config = SharedModelConfig

class CurrentGameweek(BaseModel):
    """A simple schema to return the current gameweek ID."""
    current_gameweek: int

class PlayerContext(Player):
    """
    A specialized schema for the MCP context endpoint.
    It enriches the base Player model with additional related information,
    such as team details and upcoming fixtures.
    """
    team_details: Optional[Team] = None
    upcoming_fixtures: List[Fixture] = []