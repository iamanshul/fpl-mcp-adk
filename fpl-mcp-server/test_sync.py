# test_sync.py
# Assuming app/services/fpl_sync.py exists and contains sync_all_fpl_data
from app.services import fpl_sync

if __name__ == "__main__":
    print("--- Starting Local Sync Test ---")
    fpl_sync.sync_all_fpl_data()
    print("--- Local Sync Test Finished ---")