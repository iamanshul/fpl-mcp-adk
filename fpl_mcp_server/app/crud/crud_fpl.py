#app/crud/crud_fpl.py
from google.cloud import firestore
from app.core.config import get_settings
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone



settings = get_settings()

#Initiate the Firestore client
try:
    db = firestore.Client(project=settings.GCP_PROJECT_ID)
except Exception as e:
    print(f"Error connecting to Firestore: {e}")
    db = None
    
def get_player_by_id(player_id: int) -> Optional[Dict[str, Any]]:
    """ Retrieves the single player document from the 'players' collection in Firestore
"""
    if not db:
        return None
    else:
        doc_ref = db.collection('players').document(str(player_id))
        doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

def get_team_by_id(team_id: int) -> Optional[Dict[str, Any]]:
    """ Retrieves the single team document from the 'teams' collection in Firestore
"""
    if not db:
        return None
    else:
        doc_ref = db.collection('teams').document(str(team_id))
        doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

def get_all_players() -> List[Dict[str, Any]]:
    """ Retrieves all players from the 'players' collection in Firestore
"""
    if not db:
        return []
    else:
        docs = db.collection('players').stream()
    players_ref = db.collection('players')
    docs = players_ref.stream()
    return [doc.to_dict() for doc in docs]


def batch_upsert_data(collection_name: str, data: List[Dict[str, Any]], id_key: str):
    """
    Performs a batch upsert operation for a list of documents into a specified collection.
    'Upsert' means it will create a new document or overwrite an existing one.
    This function processes data in chunks to respect Firestore's 500-operation limit per batch.
    """
    if not db: # Add check for db
        raise ConnectionError("Firestore client not initialized. Cannot perform batch upsert.")

    batch = db.batch()
    count = 0
    for item in data:
        doc_id_value = item.get(id_key)
        if not doc_id_value:
            continue # Skip items without a valid ID key

        doc_id = str(doc_id_value) # Use doc_id for consistency
        doc_ref = db.collection(collection_name).document(doc_id) # Use doc_id

        batch.set(doc_ref, item, merge=True)
        count += 1

        # Commit the batch when it's full (500 operations)
        if count == 500: # Changed from 499 to 500
            print(f"Committing batch of {count} documents to '{collection_name}'...")
            batch.commit()
            batch = db.batch() # Start a new batch
            count = 0

    # Commit any remaining operations in the final batch, outside the loop
    if count > 0:
        print(f"Committing final batch of {count} documents to '{collection_name}'...")
        batch.commit()
            
def delete_collection(collection_name: str, batch_size: int = 500):
    """
    Deletes all documents in a collection in batches.
    """
    if not db:
        raise ConnectionError("Firestore client not initialized.")

    coll_ref = db.collection(collection_name)
    # Use a loop that keeps fetching until no more documents are found
    while True:
        docs = coll_ref.limit(batch_size).stream()
        deleted_in_batch = 0

        batch_to_delete = db.batch() # Use a batch for deletion too!
        for doc in docs:
            batch_to_delete.delete(doc.reference)
            deleted_in_batch += 1

        if deleted_in_batch > 0:
            batch_to_delete.commit()
            print(f"Deleted {deleted_in_batch} documents from '{collection_name}'.")

        if deleted_in_batch < batch_size: # If less than a full batch was found, we're done
            break

def get_sync_metadata(data_type: str) -> Optional[datetime]:
    """
    Retrieves the last synchronization timestamp for a given data type.
    """
    if not db:
        return None
    doc_ref = db.collection('sync_metadata').document(data_type)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('last_updated_at')
    else:
        return None

def update_sync_metadata(data_type: str):
    """
    Updates the synchronization timestamp for a given data type to the current time.
    """
    if not db: raise ConnectionError("Firestore client not initialized.")
    doc_ref = db.collection("sync_metadata").document(data_type)
    # Use server_timestamp for accuracy, but fallback to client time if needed.
    # For this implementation, client UTC time is sufficient.
    doc_ref.set({"last_updated_at": datetime.now(timezone.utc)})


            
def get_all_from_collection(collection_name: str) -> List[Dict[str,Any]]:
    """Retrieves all documents from a specified collection."""
    if not db:
        return
    ref = db.collection(collection_name)
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]

# Add these new functions
def get_all_teams() -> List[Dict[str, Any]]:
    """ Retrieves all teams from the 'teams' collection in Firestore """
    if not db:
        return []
    docs = db.collection('teams').stream()
    return [doc.to_dict() for doc in docs]

def get_all_gameweeks() -> List[Dict[str, Any]]:
    """ Retrieves all gameweeks from the 'gameweeks' collection in Firestore """
    if not db:
        return []
    docs = db.collection('gameweeks').stream()
    return [doc.to_dict() for doc in docs]

# Add this new function
def get_current_gameweek() -> Optional[int]:
    """
    Retrieves the ID of the current gameweek from the 'gameweeks' collection.
    Assumes gameweeks have an 'is_current' field.
    """
    if not db:
        return None
    
    # Query for the gameweek where 'is_current' is true
    current_gw_docs = db.collection('gameweeks').where('is_current', '==', True).limit(1).stream()
    
    for doc in current_gw_docs:
        # Assuming the gameweek ID is stored in the 'id' field of the document
        return doc.to_dict().get('id')
    
    return None # No current gameweek found
