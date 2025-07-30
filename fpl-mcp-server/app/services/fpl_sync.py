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
This module handles the synchronization of data from the official FPL API
to the Firestore database.

It includes functions for fetching data, checking for staleness, and calculating
and syncing league standings.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List

import requests

from app.core.config import get_settings
from app.crud import crud_fpl

settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _is_data_stale(data_type: str) -> bool:
    """
    Checks if the data for a given type is stale based on the last sync time.
    """
    last_sync_time = crud_fpl.get_sync_metadata(data_type)
    if not last_sync_time:
        logging.info("No sync metadata found for '%s'. Data is considered stale.", data_type)
        return True

    if last_sync_time.tzinfo is None:
        last_sync_time = last_sync_time.replace(tzinfo=timezone.utc)

    time_since_sync = datetime.now(timezone.utc) - last_sync_time
    is_stale = time_since_sync > timedelta(hours=settings.SYNC_INTERVAL_HOURS)

    if is_stale:
        logging.info("Data for '%s' is stale (last sync: %s ago).", data_type, time_since_sync)
    else:
        logging.info("Data for '%s' is fresh (last sync: %s ago). Skipping sync.", data_type, time_since_sync)

    return is_stale

def fetch_from_fpl_api(endpoint: str) -> List[Dict[str, Any]] | Dict[str, Any] | None:
    """Fetches data from a specified FPL API endpoint."""
    url = f"{settings.FPL_API_BASE_URL}/{endpoint}"
    logging.info("Fetching data from %s", url)
    try:
        response = requests.get(url)
        response.raise_for_status()
        logging.info("Successfully fetched data from %s.", endpoint)
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("Error fetching data from %s: %s", endpoint, e)
        return None

def calculate_and_sync_standings():
    """
    Calculates Premier League standings from finished fixtures and syncs to Firestore.
    """
    logging.info("Calculating and syncing Premier League standings...")
    try:
        teams = crud_fpl.get_all_from_collection("teams")
        finished_games = [f for f in crud_fpl.get_all_from_collection("fixtures") if f.get("finished")]

        if not teams:
            logging.error("No teams found in Firestore for standings calculation.")
            return

        standings = {
            team["id"]:
            {
                "team_id": team["id"],
                "team_name": team["name"],
                "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0
            } for team in teams
        }

        for game in finished_games:
            home_team_id, away_team_id = game.get("team_h"), game.get("team_a")
            h_score, a_score = game.get("team_h_score"), game.get("team_a_score")

            if home_team_id not in standings or away_team_id not in standings:
                continue

            standings[home_team_id]["played"] += 1
            standings[home_team_id]["goals_for"] += h_score
            standings[home_team_id]["goals_against"] += a_score

            standings[away_team_id]["played"] += 1
            standings[away_team_id]["goals_for"] += a_score
            standings[away_team_id]["goals_against"] += h_score

            if h_score > a_score:
                standings[home_team_id]["wins"] += 1
                standings[home_team_id]["points"] += 3
                standings[away_team_id]["losses"] += 1
            elif a_score > h_score:
                standings[away_team_id]["wins"] += 1
                standings[away_team_id]["points"] += 3
                standings[home_team_id]["losses"] += 1
            else:
                standings[home_team_id]["draws"] += 1
                standings[away_team_id]["draws"] += 1
                standings[home_team_id]["points"] += 1
                standings[away_team_id]["points"] += 1

        standings_list = list(standings.values())
        for s in standings_list:
            s["goal_difference"] = s["goals_for"] - s["goals_against"]

        sorted_standings = sorted(
            standings_list,
            key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
            reverse=True
        )

        for i, team_standing in enumerate(sorted_standings):
            team_standing["position"] = i + 1

        crud_fpl.batch_upsert_data("league_standings", sorted_standings, "team_id")
        logging.info("Premier League standings updated for %d teams.", len(sorted_standings))

    except Exception as e:
        logging.error("An unexpected error occurred while updating standings: %s", e)

def _sync_data_type(collection_name: str, id_key: str, fetch_func: Callable[[], List[Dict[str, Any]]]):
    """
    A generic function to handle the synchronization process for a single data type.
    """
    if _is_data_stale(collection_name):
        logging.info("Proceeding with sync for '%s'...", collection_name)

        new_data = fetch_func()
        if not new_data:
            logging.error("Sync failed for '%s': No data fetched.", collection_name)
            return

        logging.info("Deleting all existing documents from '%s' collection...", collection_name)
        crud_fpl.delete_collection(collection_name)
        logging.info("Deletion complete for '%s'.", collection_name)

        logging.info("Writing %d new documents to '%s'...", len(new_data), collection_name)
        crud_fpl.batch_upsert_data(collection_name, new_data, id_key)
        logging.info("Write complete for '%s'.", collection_name)

        crud_fpl.update_sync_metadata(collection_name)
        logging.info("Sync metadata updated for '%s'.", collection_name)

def sync_all_fpl_data():
    """
    Coordinates the full data synchronization process from the FPL API to Firestore.
    """
    logging.info("Starting FPL data synchronization...")

    bootstrap_data = fetch_from_fpl_api("bootstrap-static/")
    if bootstrap_data:
        _sync_data_type("players", "id", lambda: bootstrap_data.get("elements", []))
        _sync_data_type("teams", "id", lambda: bootstrap_data.get("teams", []))
        _sync_data_type("gameweeks", "id", lambda: bootstrap_data.get("events", []))
    else:
        logging.error("Could not fetch bootstrap data. Skipping related syncs.")

    _sync_data_type("fixtures", "id", lambda: fetch_from_fpl_api("fixtures/"))

    calculate_and_sync_standings()

    logging.info("FPL data synchronization complete.")