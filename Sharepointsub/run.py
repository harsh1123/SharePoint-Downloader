"""
Script to run the Organizational SharePoint Sync Tool.
This is a self-contained script that runs the sync tool without dependencies on the parent folder.
"""
import os
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Load environment variables from .env file
env_path = os.path.join(current_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")
    print("Please create a .env file with your SharePoint credentials.")
    print("You can use the .env.template file as a starting point.")

# Import the sync manager
from manual_sync_manager import ManualSyncManager
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
    parser = argparse.ArgumentParser(description='Organizational SharePoint Sync Tool')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    parser.add_argument('--check-only', action='store_true', help='Check for changes but don\'t download')
    args = parser.parse_args()

    setup_logging()

    logging.info("=" * 80)
    logging.info("Organizational SharePoint Sync Tool".center(80))
    logging.info("=" * 80)

    try:
        sync_manager = ManualSyncManager(check_only=args.check_only)

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
