#app/schemas/fpl_schema.py
import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Optional, List, Dict, Any
from datetime import datetime


SharedModelConfig = ConfigDict(from_attributes=True)

class Team(BaseModel):
    id : int
    name:str
    short_name:str
    code: int
    strength: int
    strength_overall_home: int
    strength_overall_away: int
    strength_attack_home: int
    strength_attack_away: int
    strength_defence_home: int
    strength_defence_away: int
    pulse_id: int # Or whatever the actual field name for pulse ID is
    model_config = SharedModelConfig

        
class Player(BaseModel):
    id: int
    code: int
    element_type: int # FPL API: integer ID for position (1=GK, 2=DEF, 3=MID, 4=FWD)
    event_points: int # FPL API: points from the most recent gameweek
    first_name: str
    second_name: str
    web_name: str
    team: int # FPL API: ID of the team the player belongs to
    team_code: int # FPL API: Numeric code for the team
    now_cost: int # FPL API: player's current cost in pence (e.g., 41 for 4.1m)
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
    form: str # FPL API: typically a string float (e.g., "1.5")
    points_per_game: str # FPL API: typically a string float (e.g., "2.3")
    selected_by_percent: str # FPL API: typically a string float (e.g., "0.1")
    influence: str # FPL API: string float
    creativity: str # FPL API: string float
    threat: str # FPL API: string float
    ict_index: str # FPL API: string float
    chance_of_playing_this_round: Optional[int] = None # FPL API: 0, 50, 75, 100
    chance_of_playing_next_round: Optional[int] = None # FPL API: 0, 50, 75, 100
    ep_next: Optional[str] = None # FPL API: expected points next gameweek (string float)
    ep_this: Optional[str] = None # FPL API: expected points this gameweek (string float)
    news: str # Player news/injury status
    news_added: Optional[datetime] = None # Timestamp of news update

    # Fields that your previous SQLite schema used for optimization (derived/calculated in your sync).
    # If these are stored as distinct fields in Firestore, keep them. Otherwise, consider if they should be computed fields.
    fixture_difficulty: Optional[float] = None
    recent_form: Optional[float] = None
    next_game_opponent: Optional[str] = None
    is_home: Optional[int] = None # 0 or 1
    
    model_config = SharedModelConfig
    _POSITION_MAP = {
        1: "Goalkeeper",
        2: "Defender",
        3: "Midfielder",
        4: "Forward",
    }
    @computed_field
    @property
    def player_name(self) -> str:
        return f"{self.first_name} {self.second_name}"
    @computed_field
    @property
    def position(self) -> str:
        return self._POSITION_MAP.get(self.element_type, "Unknown")
    @computed_field
    @property
    def cost(self) -> float:
        return self.now_cost / 10.0 # Convert pence to pounds
    @computed_field
    @property
    def last_game_points(self) -> int:
        return self.event_points

        
class Fixture(BaseModel):
    id: int
    code: int
    event: Optional[int]
    finished: bool
    kickoff_time: Optional[datetime]
    team_h: int # Matches FPL API: Home team ID (required)
    team_a: int # Matches FPL API: Away team ID (required)
    team_h_score: Optional[int] = None # Matches FPL API: Home team score (Optional, as it's None for future games)
    team_a_score: Optional[int] = None # Matches FPL API: Away team score (Optional, as it's None for future games)

    team_h_difficulty: int # Matches FPL API: Home team's fixture difficulty (1-5)
    team_a_difficulty: int # Matches FPL API: Away team's fixture difficulty (1-5)
    
    # 'stats' field is a list of dictionaries with complex structure.
    stats: List[Dict[str, Any]] = []
    model_config = SharedModelConfig
    
class GameStat(BaseModel):
    """
    Represents the overall game statistics, likely from the FPL API's 'bootstrap-static' endpoint.
    This model aggregates various data points like phases, elements (players), teams, and events (gameweeks).
    """
    stat_id: Optional[int] = None # Auto-incrementing, can be None on insert
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
    
# The Gameweek model seems to reflect FPL API's "event" data, not a SQLite table in your schema.
# It's fine if its purpose is to process that specific API endpoint.
class Gameweek(BaseModel):
    id: int
    name: str
    deadline_time: datetime
    deadline_time_epoch: Optional[int] = None # Ensure this is Optional
    average_entry_score: int
    finished: bool
    data_checked: bool
    highest_scoring_entry: Optional[int] = None
    highest_score: Optional[int] = None
    deadline_time_game_offset: Optional[int] = None # Ensure this is Optional

    # FIX: These MUST be Optional, as the data sometimes does not include them.
    deadline_time_formatted: Optional[str] = None
    finished_provisional: Optional[bool] = None

    is_previous: bool
    is_current: bool
    is_next: bool

    # Other fields from FPL 'events' that might be present:
    can_enter: Optional[bool] = None
    top_element: Optional[int] = None
    top_element_info: Optional[Dict[str, Any]] = None
    transfers_made: Optional[int] = None
    chip_plays: Optional[List[Dict[str, Any]]] = None
    most_vice_captained: Optional[int] = None
    h2h_ko_matches_created: Optional[bool] = None
    release_time: Optional[datetime] = None # Or Optional[str] if stored as string/epoch
    cup_leagues_created: Optional[bool] = None
    most_selected: Optional[int] = None
    most_captained: Optional[int] = None
    most_transferred_in: Optional[int] = None
    overrides: Optional[Dict[str, Any]] = None


    model_config = SharedModelConfig

    

# This is the schema for our special "MCP" context endpoint.
# It inherits from the Player schema and adds extra, related information.

class PlayerContext(Player):

    team_details: Optional[Team] = None # This depends on what data you combine.

    # This assumes Fixture model represents API fixtures or joined DB fixtures
    upcoming_fixtures: List[Fixture] = []


    

    

    

    


    
    
        