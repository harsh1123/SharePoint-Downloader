"""
Test script for the manual sync implementation.
"""
import os
import sys
import logging
from manual_sync_manager import ManualSyncManager
from config import STATE_FILE

def main():
    """Test the manual sync implementation."""
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Print header
    print("=" * 80)
    print("Manual Sync Test".center(80))
    print("=" * 80)
    
    # Check if state file exists
    if os.path.exists(STATE_FILE):
        print(f"State file exists at: {os.path.abspath(STATE_FILE)}")
        print(f"Size: {os.path.getsize(STATE_FILE)} bytes")
    else:
        print(f"No state file found at: {os.path.abspath(STATE_FILE)}")
    
    # Create sync manager with root-only option
    print("\nInitializing sync manager with root-only option...")
    sync_manager = ManualSyncManager(root_only=True)
    
    # Run the sync
    print("\nStarting sync process...")
    success = sync_manager.run_one_time_sync()
    
    if success:
        print("\nSync completed successfully!")
        print(f"Files processed: {sync_manager.files_processed}")
    else:
        print("\nSync failed!")
    
    # Check state file after sync
    if os.path.exists(STATE_FILE):
        print(f"\nState file updated at: {os.path.abspath(STATE_FILE)}")
        print(f"Size: {os.path.getsize(STATE_FILE)} bytes")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()
