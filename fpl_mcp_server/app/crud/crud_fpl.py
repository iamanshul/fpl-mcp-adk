#app/crud/crud_fpl.py
from google.cloud import firestore
from app.core.config import get_settings
from typing import Optional, List, Dict, Any


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



def batch_upsert_data(collection_name: str, data: List [Dict[str, Any]], id_key: str):
    """ 
    Performs a batch upsert operation for a list of documents into a specified collection.
    'Upsert' means it will create a new document or overwrite an existing one.
    This function processes data in chunks to respect Firestore's 500-operation limit per batch.
    """
    batch = db.batch()
    count = 0
    for item in data:
        doc_id_value = item.get(id_key)
        if not doc_id_value:
            continue
        doc_id = str(doc_id_value)
        doc_ref = db.collection(collection_name).document(str(doc_id_value))
        #use set() with merge = True to create or overwrite the document
        batch.set(doc_ref, item, merge=True)
        count += 1
        #Firestore batch writes have a limit of 500 operations
        #We commit the batch when its full the start the new one.
        if count == 499:
            print(f"committing batch of {count} items to {collection_name}")
            batch.commit()
            batch = db.batch()
            count = 0
        
        #commit any remaining values
        if count > 0:
            print(f"committing remaining {count} items to {collection_name}")
            batch.commit()
            
def get_all_from_collection(collection_name: str) -> List[Any]:
    """Retrieves all documents from a specified collection."""
    if not db:
        return
    ref = db.collection(collection_name)
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]



        



    