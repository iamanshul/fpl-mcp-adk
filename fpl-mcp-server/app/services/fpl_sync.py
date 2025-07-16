#app/services/fpl_sync.py
import requests
from app.core.config import get_settings
from app.crud import crud_fpl
from typing import List, Dict, Any, Callable
from datetime import datetime, timezone, timedelta


settings = get_settings()

def _is_data_stale(data_type: str) -> bool:
    """
    Checks if the data for a given type is stale based on the last sync time.
    """
    last_sync_time = crud_fpl.get_sync_metadata(data_type)
    if not last_sync_time:
        print(f"No sync metadata found for '{data_type}'. Data is considered stale.")
        return True
    
    # Ensure last_sync_time is timezone-aware for correct comparison
    if last_sync_time.tzinfo is None:
        last_sync_time = last_sync_time.replace(tzinfo=timezone.utc)

    time_since_sync = datetime.now(timezone.utc) - last_sync_time
    is_stale = time_since_sync > timedelta(hours=settings.SYNC_INTERVAL_HOURS)
    
    if is_stale:
        print(f"Data for '{data_type}' is stale (last sync: {time_since_sync} ago).")
    else:
        print(f"Data for '{data_type}' is fresh (last sync: {time_since_sync} ago). Skipping sync.")
        
    return is_stale

def fetch_from_fpl_api(endpoint: str) -> List[Dict[str, Any]]| Dict[str, Any] | None:
    """Fetches data from a specified FPL API endpoint."""
    url = f"{settings.FPL_API_BASE_URL}/{endpoint}"
    print(f"Fetching data from {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"Successfully fetched data from {endpoint}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {endpoint}: {e}")
        return None


def calculate_and_sync_standings():
    """
    Calculates the Premier League standings based on finished fixtures
    and syncs the result to a 'league_standings' collection in Firestore.
    """
    print("Calculating and syncing Premier League standings...")
    try:
        # Instead of querying a DB, we get data from our Firestore cache
        teams = crud_fpl.get_all_from_collection("teams")
        finished_games = [f for f in crud_fpl.get_all_from_collection("fixtures") if f.get('finished')]

        if not teams:
            print("Error: No teams found in Firestore for standings calculation.")
            return
        
        # Use team 'id' as the key for the standings dictionary
        standings = {
            team['id']: {
                'team_id': team['id'],
                'team_name': team['name'],
                'played': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                'goals_for': 0, 'goals_against': 0, 'points': 0
            } for team in teams
        }

        for game in finished_games:
            home_team_id, away_team_id = game.get('team_h'), game.get('team_a')
            h_score, a_score = game.get('team_h_score'), game.get('team_a_score')

            if home_team_id not in standings or away_team_id not in standings:
                continue

            # Update stats for both home and away teams
            standings[home_team_id]['played'] += 1
            standings[home_team_id]['goals_for'] += h_score
            standings[home_team_id]['goals_against'] += a_score

            standings[away_team_id]['played'] += 1
            standings[away_team_id]['goals_for'] += a_score
            standings[away_team_id]['goals_against'] += h_score

            # Assign points
            if h_score > a_score:
                standings[home_team_id]['wins'] += 1
                standings[home_team_id]['points'] += 3
                standings[away_team_id]['losses'] += 1
            elif a_score > h_score:
                standings[away_team_id]['wins'] += 1
                standings[away_team_id]['points'] += 3
                standings[home_team_id]['losses'] += 1
            else:
                standings[home_team_id]['draws'] += 1
                standings[away_team_id]['draws'] += 1
                standings[home_team_id]['points'] += 1
                standings[away_team_id]['points'] += 1
        
        # Prepare data for Firestore, calculating goal difference
        standings_list = list(standings.values())
        for s in standings_list:
            s['goal_difference'] = s['goals_for'] - s['goals_against']

        # Sort by points, then goal difference, then goals for
        sorted_standings = sorted(
            standings_list, 
            key=lambda x: (x['points'], x['goal_difference'], x['goals_for']), 
            reverse=True
        )

        # Add position rank
        for i, team_standing in enumerate(sorted_standings):
            team_standing['position'] = i + 1

        # Upsert the calculated standings into the new collection
        crud_fpl.batch_upsert_data("league_standings", sorted_standings, "team_id")
        print(f"Premier League standings updated for {len(sorted_standings)} teams.")

    except Exception as e:
        print(f"An unexpected error occurred while updating standings: {e}")
        
def _sync_data_type(collection_name: str, id_key: str, fetch_func: Callable[[], List[Dict[str, Any]]]):
    """
    Generic function to handle the sync process for a single data type.
    Checks for staleness, deletes old data, fetches new data, and writes it.
    """
    if _is_data_stale(collection_name):
        print(f"Proceeding with sync for '{collection_name}'...")
        
        # 1. Fetch new data from the FPL API
        new_data = fetch_func()
        if not new_data:
            print(f"Sync failed for '{collection_name}': No data fetched.")
            return

        # 2. Delete all old documents from the collection
        print(f"Deleting all existing documents from '{collection_name}' collection...")
        crud_fpl.delete_collection(collection_name)
        print(f"Deletion complete for '{collection_name}'.")

        # 3. Write the new data to the collection
        print(f"Writing {len(new_data)} new documents to '{collection_name}'...")
        crud_fpl.batch_upsert_data(collection_name, new_data, id_key)
        print(f"Write complete for '{collection_name}'.")

        # 4. Update the sync metadata timestamp
        crud_fpl.update_sync_metadata(collection_name)
        print(f"Sync metadata updated for '{collection_name}'.")
    else:
        # If data is not stale, we do nothing.
        pass

def sync_all_fpl_data():
    """
    Coordinates the full data synchronization process.
    Fetches data from the FPL API and upserts it into the respective Firestore collections.
    """
    print("Starting FPL data synchronization...")
    # Sync static data (players, teams, gameweeks)
    
    bootstrap_data = fetch_from_fpl_api("bootstrap-static/")
    if bootstrap_data:
        _sync_data_type("players", "id", lambda: bootstrap_data.get("elements",))
        _sync_data_type("teams", "id", lambda: bootstrap_data.get("teams",))
        _sync_data_type("gameweeks", "id", lambda: bootstrap_data.get("events",))
    else:
        print("Could not fetch bootstrap data. Skipping related syncs.")
    
    _sync_data_type("fixtures", "id", lambda: fetch_from_fpl_api("fixtures"))

    calculate_and_sync_standings()
    
    print("FPL data synchronization complete.")
