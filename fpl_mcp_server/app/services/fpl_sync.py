#app/services/fpl_sync.py
import requests
from app.core.config import get_settings
from app.crud import crud_fpl
from typing import List, Dict, Any

settings = get_settings()

def fetch_from_fpl_api(endpoint: str) -> List[Dict[str, Any]]| None:
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
        teams = crud_fpl.get_all_teams()
        finished_games = [f for f in crud_fpl.get_all_fixtures() if f.get('finished')]

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

def sync_all_fpl_data():
    """
    Coordinates the full data synchronization process.
    Fetches data from the FPL API and upserts it into the respective Firestore collections.
    """
    print("Starting FPL data synchronization...")
    # Sync static data (players, teams, gameweeks)
    
    bootstrap_data = fetch_from_fpl_api("bootstrap-static/")
    if bootstrap_data:
        try:
            players = bootstrap_data.get("elements", [])
            if players:
                print(f"Upserting {len(players)} players...")
                crud_fpl.batch_upsert_data("players", players, "id")
            teams = bootstrap_data.get("teams", [])
            if teams:
                print(f"Upserting {len(teams)} teams...")
                crud_fpl.batch_upsert_data("teams", teams, "id")
            gameweeks = bootstrap_data.get("events", [])
            if gameweeks:
                print(f"Upserting {len(gameweeks)} gameweeks...")
                crud_fpl.batch_upsert_data("gameweeks", gameweeks, "id")
        except Exception as e:
           print(f"Error upserting data: {e}")
           
    fixtures_data = fetch_from_fpl_api("fixtures/")
    if fixtures_data:
        try:
            print(f"Upserting {len(fixtures_data)} fixtures...")
            crud_fpl.batch_upsert_data("fixtures", fixtures_data, "id")
        except Exception as e:
            print(f"Error upserting data: {e}")
    
  #  standings_data = fetch_from_fpl_api("standings/") commenting for now. need to check
    calculate_and_sync_standings()
    
    print("FPL data synchronization complete.")
