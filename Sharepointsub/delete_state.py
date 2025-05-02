"""
Script to delete the state file.
"""
import os
import sys
from config import STATE_FILE

def main():
    """Delete the state file."""
    print(f"Looking for state file at: {os.path.abspath(STATE_FILE)}")
    
    if os.path.exists(STATE_FILE):
        print(f"State file found. Size: {os.path.getsize(STATE_FILE)} bytes")
        
        try:
            os.remove(STATE_FILE)
            print("State file deleted successfully.")
        except Exception as e:
            print(f"Error deleting state file: {str(e)}")
            return 1
    else:
        print("No state file found.")
    
    # Check for backup files
    backup_file = f"{STATE_FILE}.bak"
    if os.path.exists(backup_file):
        print(f"Backup state file found at: {os.path.abspath(backup_file)}")
        
        try:
            os.remove(backup_file)
            print("Backup state file deleted successfully.")
        except Exception as e:
            print(f"Error deleting backup state file: {str(e)}")
    
    # Check for temp files
    temp_file = f"{STATE_FILE}.tmp"
    if os.path.exists(temp_file):
        print(f"Temporary state file found at: {os.path.abspath(temp_file)}")
        
        try:
            os.remove(temp_file)
            print("Temporary state file deleted successfully.")
        except Exception as e:
            print(f"Error deleting temporary state file: {str(e)}")
    
    print("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
