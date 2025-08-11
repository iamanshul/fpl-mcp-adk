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
This module contains all the CRUD (Create, Read, Update, Delete) operations
for interacting with the Firestore database for the FPL application.

It handles fetching and updating data for players, teams, gameweeks, and 
synchronization metadata.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import operator
from google.cloud import firestore

from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    db = firestore.Client(project=settings.GCP_PROJECT_ID)
    logging.info("Successfully connected to Firestore.")
except Exception as e:
    logging.error("Error connecting to Firestore: %s", e)
    db = None

def get_player_by_id(player_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single player document from Firestore by their ID."""
    if not db:
        return None
    doc_ref = db.collection("players").document(str(player_id))
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def get_team_by_id(team_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single team document from Firestore by their ID."""
    if not db:
        return None
    doc_ref = db.collection("teams").document(str(team_id))
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

def get_all_players() -> List[Dict[str, Any]]:
    """Retrieves all player documents from the 'players' collection."""
    if not db:
        return []
    docs = db.collection("players").stream()
    return [doc.to_dict() for doc in docs]

def batch_upsert_data(collection_name: str, data: List[Dict[str, Any]], id_key: str):
    """
    Performs a batch upsert (update or insert) operation into a Firestore collection.
    Handles Firestore's 500-operation limit per batch.
    """
    if not db:
        raise ConnectionError("Firestore client not initialized.")

    batch = db.batch()
    count = 0
    for item in data:
        if not (doc_id_value := item.get(id_key)):
            continue

        doc_ref = db.collection(collection_name).document(str(doc_id_value))
        batch.set(doc_ref, item, merge=True)
        count += 1

        if count == 500:
            logging.info("Committing batch of %d documents to '%s'...", count, collection_name)
            batch.commit()
            batch = db.batch()
            count = 0

    if count > 0:
        logging.info("Committing final batch of %d documents to '%s'...", count, collection_name)
        batch.commit()

def delete_collection(collection_name: str, batch_size: int = 500):
    """Deletes all documents within a specified Firestore collection in batches."""
    if not db:
        raise ConnectionError("Firestore client not initialized.")

    coll_ref = db.collection(collection_name)
    while True:
        docs = coll_ref.limit(batch_size).stream()
        deleted_in_batch = 0
        batch_to_delete = db.batch()
        for doc in docs:
            batch_to_delete.delete(doc.reference)
            deleted_in_batch += 1

        if deleted_in_batch > 0:
            batch_to_delete.commit()
            logging.info("Deleted %d documents from '%s'.", deleted_in_batch, collection_name)

        if deleted_in_batch < batch_size:
            break

def get_sync_metadata(data_type: str) -> Optional[datetime]:
    """Retrieves the last synchronization timestamp for a given data type."""
    if not db:
        return None
    doc_ref = db.collection("sync_metadata").document(data_type)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("last_updated_at")
    return None

def update_sync_metadata(data_type: str):
    """Updates the synchronization timestamp for a given data type to the current time."""
    if not db:
        raise ConnectionError("Firestore client not initialized.")
    doc_ref = db.collection("sync_metadata").document(data_type)
    doc_ref.set({"last_updated_at": datetime.now(timezone.utc)})

def get_all_from_collection(collection_name: str) -> List[Dict[str, Any]]:
    """Retrieves all documents from a specified Firestore collection."""
    if not db:
        return []
    ref = db.collection(collection_name)
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]

def get_all_teams() -> List[Dict[str, Any]]:
    """Retrieves all team documents from the 'teams' collection."""
    if not db:
        return []
    docs = db.collection("teams").stream()
    return [doc.to_dict() for doc in docs]

def get_all_gameweeks() -> List[Dict[str, Any]]:
    """Retrieves all gameweek documents from the 'gameweeks' collection."""
    if not db:
        return []
    docs = db.collection("gameweeks").stream()
    return [doc.to_dict() for doc in docs]

def get_current_gameweek() -> Optional[int]:
    """
    Finds and returns the ID of the current gameweek.
    If no gameweek is marked as current, it finds the next upcoming gameweek.
    """
    if not db:
        return None

    # First, try to find the gameweek explicitly marked as current
    current_gw_docs = db.collection("gameweeks").where("is_current", "==", True).limit(1).stream()
    for doc in current_gw_docs:
        return doc.to_dict().get("id")

    # If no gameweek is current, find the next one that hasn't finished
    logging.warning("No current gameweek found. Searching for the next upcoming gameweek.")
    all_gameweeks = get_all_gameweeks()
    upcoming_gameweeks = [gw for gw in all_gameweeks if not gw.get("finished")]
    
    if not upcoming_gameweeks:
        logging.warning("No upcoming gameweeks found. Defaulting to Gameweek 1.")
        return 1 #As no games are finished

    # Sort by deadline time to find the earliest upcoming one
    next_gameweek = sorted(upcoming_gameweeks, key=lambda gw: gw.get("deadline_time"))[0]
    return next_gameweek.get("id")

def search_players(
    name: Optional[str] = None,
    team: Optional[str] = None,
    position: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = 10,
) -> List[Dict[str, Any]]:
    """
    Searches for players with robust, dynamic filtering and sorting.
    """
    logging.info("Advanced search with name: %s, team: %s, position: %s, filters: %s, sort_by: %s", name, team, position, filters, sort_by)

    players_to_filter = get_all_players()

    # --- Basic text search ---
    if name:
        name_lower = name.lower()
        players_to_filter = [
            p for p in players_to_filter if (
                name_lower in p.get("web_name", "").lower() or
                name_lower in p.get("first_name", "").lower() or
                name_lower in p.get("second_name", "").lower()
            )
        ]
    if team:
        all_teams = get_all_teams()
        team_id = next((t["id"] for t in all_teams if t["name"].lower() == team.lower()), None)
        if team_id:
            players_to_filter = [p for p in players_to_filter if p.get("team") == team_id]
        else:
            return []
            
    if position:
        # Correctly map position name to element_type ID for filtering
        pos_map = {"goalkeeper": 1, "defender": 2, "midfielder": 3, "forward": 4}
        pos_id = pos_map.get(position.lower())
        if pos_id:
            players_to_filter = [p for p in players_to_filter if p.get("element_type") == pos_id]
        else:
            # Invalid position name passed
            return []

    # --- Dynamic Filtering Engine ---
    if filters:
        ops = {
            'eq': operator.eq, 'ne': operator.ne,
            'gt': operator.gt, 'gte': operator.ge,
            'lt': operator.lt, 'lte': operator.le,
        }
        for f in filters:
            field, op_str, value = f.get('field'), f.get('operator'), f.get('value')
            if not all([field, op_str, value is not None]):
                continue

            op_func = ops.get(op_str)
            if not op_func:
                continue

            current_list = []
            for p in players_to_filter:
                player_value = p.get(field)
                if player_value is None:
                    continue
                try:
                    if op_func(player_value, type(player_value)(value)):
                        current_list.append(p)
                except (ValueError, TypeError):
                    continue
            players_to_filter = current_list

    # --- Sorting Logic ---
    if sort_by:
        # Sorts by the specified field, descending. Handles missing keys gracefully.
        # Added a try-except to handle sorting non-numeric types
        try:
            players_to_filter.sort(key=lambda p: float(p.get(sort_by, 0)), reverse=True)
        except (ValueError, TypeError):
            players_to_filter.sort(key=lambda p: str(p.get(sort_by, "")), reverse=True)


    # --- Limit Results ---
    return players_to_filter[:limit] if limit else players_to_filter


    





    

def search_teams(name: str = None) -> List[Dict[str, Any]]:
    """
    Searches for teams by name, checking against full and short names.
    """
    logging.info("Searching for teams with name: %s", name)
    all_teams = get_all_teams()
    if not name:
        return []

    name_lower = name.lower()
    return [
        t for t in all_teams if (
            name_lower in t.get("name", "").lower() or
            name_lower in t.get("short_name", "").lower()
        )
    ]