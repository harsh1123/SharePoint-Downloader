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
    args = parser.parse_args()

    # Set up logging
    setup_logging()

    # Log command line arguments
    logging.debug(f"Command line arguments: {args}")

    try:
        logging.info("Initializing sync manager...")
        sync_manager = SyncManager()

        if args.check_only:
            logging.info("Running in check-only mode (no downloads)")
            # TODO: Implement check-only mode
            logging.warning("Check-only mode not fully implemented yet")

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
