#app/schemas/fpl_schema.py
import datetime
from pydantic import BaseModel
from typing import Optional, List

class OrmConfig:
    """Pydantic config to allow mapping from ORM objects or dicts."""
    orm_mode = True

class Team(BaseModel):
    id = int
    name:str
    short_name:str
    class Config(OrmConfig):
        #this allows the Pydantic model to be created from arbitary class instances
        #which is useful when mapping from database objects
        pass
        
class Player(BaseModel):
    id: int
    player_name: str # Matches SQLite
    web_name: str
    team: str # Matches SQLite (team name)
    position: str # Matches SQLite (e.g., "Goalkeeper")
    cost: float # Matches SQLite type
    total_points: int
    last_game_points: int # Matches SQLite
    points_per_game: float # Matches SQLite type
    selected_by_percent: float # Matches SQLite type
    form: float # Matches SQLite type
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    yellow_cards: int
    red_cards: int
    penalties_saved: int
    saves: int
    bonus: int
    bps: int
    ict_index: float # Matches SQLite type
    starts_per_90: float # Matches SQLite
    status: str # Matches SQLite
    chance_of_playing_this_round: Optional[float] = None # Matches SQLite type
    news: str
    news_added: Optional[str] = None # SQLite stores as TEXT, Pydantic can parse datetime from string

    # Important fields from SQLite's players table for optimization:
    fixture_difficulty: Optional[float] = None # Matches SQLite
    recent_form: Optional[float] = None # Matches SQLite
    next_game_opponent: Optional[str] = None # Matches SQLite
    is_home: Optional[int] = None # Matches SQLite (0 or 1)
    
    class Config:
        orm_mode = True
        
class Fixture(BaseModel):
    id: int
    gameweek: Optional[int] # Matches SQLite column name 'gameweek'
    home_team: str        # Matches SQLite column 'home_team'
    away_team: str        # Matches SQLite column 'away_team'
    home_team_score: Optional[int]
    away_team_score: Optional[int]
    kickoff_time: Optional[datetime]
    team_h_difficulty: int
    team_a_difficulty: int
    finished: bool
     # 'stats' is likely from the raw FPL API response, not directly stored in pl_schedule
    # Keep it if you use this model to process the raw API fixture data
    stats: List[Dict[str, Any]] = [] # Example: List of generic stat dictionaries
    class Config(OrmConfig):
        pass
    
class GameStats(BaseModel):
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
    class Config(OrmConfig):
        pass

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
    
    class Config(OrmConfig):
        pass
    
# The Gameweek model seems to reflect FPL API's "event" data, not a SQLite table in your schema.
# It's fine if its purpose is to process that specific API endpoint.
class Gameweek(BaseModel):
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0

    class Config(OrmConfig):
        pass

    

# This is the schema for our special "MCP" context endpoint.
# It inherits from the Player schema and adds extra, related information.

class PlayerContext(Player):
    # Here, team_details might refer to the *full* FPL API Team object, not the slim DB Team.
    # If so, you'd need a separate Team model that includes all the FPL API fields.
    # For now, let's assume it's still referring to the slim Team if fetched from DB joins.
    # If this is for API response building, you'd put the full FPL API Team data here.
    team_details: Optional[Team] = None # This depends on what data you combine.

    # This assumes Fixture model represents API fixtures or joined DB fixtures
    upcoming_fixtures: List[Fixture] = []


    

    

    

    


    
    
        