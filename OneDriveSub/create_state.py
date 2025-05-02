"""
Simple script to directly create a state file.
"""
import os
import json
import time
from datetime import datetime

# Define the state file path
# Use the same location as in config.py
HOME_DIR = os.path.expanduser("~")
STATE_FILE = os.path.join(HOME_DIR, "onedrive_sync_state.json")

def create_state_file():
    """Create a state file with a dummy delta link."""
    try:
        # Create a dummy delta link
        dummy_delta_link = f"https://graph.microsoft.com/v1.0/me/drive/root/delta?token=dummy_{int(time.time())}"

        # Create the state object
        state = {
            "delta_link": dummy_delta_link,
            "last_sync": datetime.now().isoformat()
        }

        # Ensure the directory exists
        state_dir = os.path.dirname(STATE_FILE)
        if state_dir and not os.path.exists(state_dir):
            os.makedirs(state_dir, exist_ok=True)

        # Write the state file
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"State file created successfully at: {os.path.abspath(STATE_FILE)}")
        print(f"State file contents: {state}")

        # Verify the file was created
        if os.path.exists(STATE_FILE):
            file_size = os.path.getsize(STATE_FILE)
            print(f"File size: {file_size} bytes")
            return True
        else:
            print(f"Failed to create state file")
            return False

    except Exception as e:
        print(f"Error creating state file: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("Creating state file...")
    success = create_state_file()
    if success:
        print("State file created successfully")
    else:
        print("Failed to create state file")
