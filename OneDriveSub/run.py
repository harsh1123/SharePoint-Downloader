"""
Main entry point for the OneDrive Sync Tool for individual users.
"""
import os
import sys
import logging
import argparse
import traceback
from datetime import datetime
from sync_manager import SyncManager
from config import LOG_FILE, DEBUG_LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT

def setup_logging():
    """Set up logging configuration."""
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Convert string log level to logging constant
    log_level = getattr(logging, LOG_LEVEL)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            # Regular log file with INFO level
            logging.FileHandler(LOG_FILE),
            # Debug log file with DEBUG level
            logging.FileHandler(DEBUG_LOG_FILE),
            # Console output
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific log levels for different handlers
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            if handler.baseFilename == DEBUG_LOG_FILE:
                # Debug log gets everything
                handler.setLevel(logging.DEBUG)
            else:
                # Regular log gets INFO and above
                handler.setLevel(logging.INFO)

    # Configure logging for requests and urllib3
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)

    # Log system information
    logging.info("=" * 80)
    logging.info("OneDrive Sync Tool for Individual Users".center(80))
    logging.info("=" * 80)
    logging.info(f"Python version: {sys.version}")
    logging.info(f"Operating system: {os.name}")
    logging.info(f"Log level: {LOG_LEVEL}")
    logging.info(f"Regular log file: {os.path.abspath(LOG_FILE)}")
    logging.info(f"Debug log file: {os.path.abspath(DEBUG_LOG_FILE)}")
    logging.debug("Debug logging is enabled")

def main():
    """Main function to run the sync tool."""
    parser = argparse.ArgumentParser(description='OneDrive Sync Tool for Individual Users')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    parser.add_argument('--check-only', action='store_true', help='Check for changes but don\'t download')
    parser.add_argument('--verbose', action='store_true', help='Show verbose output')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    parser.add_argument('--test', action='store_true', help='Run in test mode (limited files)')
    parser.add_argument('--max-files', type=int, default=10, help='Maximum number of files to download in test mode')
    parser.add_argument('--folder', type=str, help='Specific folder to sync (e.g., "Documents")')
    parser.add_argument('--root-only', action='store_true', help='Download only files in the root (not in any folder)')
    parser.add_argument('--create-test-state', action='store_true', help='Create a test state file (for debugging)')
    parser.add_argument('--force-full-sync', action='store_true', help='Force a full sync by ignoring the existing delta link')
    parser.add_argument('--show-state', action='store_true', help='Show the current sync state and exit')
    args = parser.parse_args()

    # Set up logging
    setup_logging()

    # Log command line arguments
    logging.debug(f"Command line arguments: {args}")

    try:
        logging.info("Initializing sync manager...")

        # Configure sync options based on command line arguments
        sync_options = {
            'check_only': args.check_only,
            'test_mode': args.test,
            'max_files': args.max_files if args.test else None,
            'target_folder': args.folder,
            'root_only': args.root_only,
            'force_full_sync': args.force_full_sync
        }

        # Log the sync options
        logging.info(f"Sync options: {sync_options}")

        # Initialize the sync manager with options
        sync_manager = SyncManager(**sync_options)

        # Handle special command-line options
        if args.create_test_state:
            logging.info("Creating test state file...")
            if sync_manager.create_test_state_file():
                logging.info("Test state file created successfully")
                return 0
            else:
                logging.error("Failed to create test state file")
                return 1

        if args.show_state:
            logging.info("Showing current sync state...")
            sync_manager.show_state()
            return 0

        if args.force_full_sync:
            logging.info("Forcing full sync by ignoring existing delta link...")
            sync_manager.delta_link = None
            logging.info("Delta link cleared. Will perform full sync.")

        # Log the sync mode
        if args.check_only:
            logging.info("Running in check-only mode (no downloads)")

        if args.test:
            logging.info(f"Running in test mode (max {args.max_files} files)")
            if args.folder:
                logging.info(f"Targeting specific folder: {args.folder}")

        if args.root_only:
            logging.info("Running in root-only mode (only files not in any folder)")

        # Log the state file path
        state_file_path = os.path.abspath(sync_manager.state_file)
        logging.info(f"Using state file: {state_file_path}")
        if os.path.exists(state_file_path):
            state_file_size = os.path.getsize(state_file_path)
            logging.info(f"State file exists. Size: {state_file_size} bytes")
        else:
            logging.info("State file does not exist yet. Will be created after successful sync.")

        # Run the sync
        if args.continuous:
            logging.info("Starting continuous sync mode")
            sync_manager.run_continuous_sync()
        else:
            logging.info("Starting one-time sync")
            success = sync_manager.run_one_time_sync()
            if success:
                logging.info("Sync completed successfully")
            else:
                logging.error("Sync failed")
                return 1

        logging.info("Program completed successfully")
        return 0

    except KeyboardInterrupt:
        logging.info("Program interrupted by user")
        return 0
    except Exception as e:
        logging.error(f"Unhandled exception: {str(e)}")
        # Log the full stack trace to the debug log
        logging.debug(f"Stack trace: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
