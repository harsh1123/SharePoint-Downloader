"""
Main entry point for the OneDrive Sync Tool for individual users.
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from sync_manager import SyncManager
from config import LOG_FILE

def setup_logging():
    """Set up logging configuration."""
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function to run the sync tool."""
    parser = argparse.ArgumentParser(description='OneDrive Sync Tool for Individual Users')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    parser.add_argument('--check-only', action='store_true', help='Check for changes but don\'t download')
    args = parser.parse_args()
    
    setup_logging()
    
    logging.info("=" * 80)
    logging.info("OneDrive Sync Tool for Individual Users".center(80))
    logging.info("=" * 80)
    
    try:
        sync_manager = SyncManager()
        
        if args.continuous:
            sync_manager.run_continuous_sync()
        else:
            success = sync_manager.run_one_time_sync()
            if success:
                logging.info("Sync completed successfully")
            else:
                logging.error("Sync failed")
                return 1
        
        return 0
    
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
