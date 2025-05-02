"""
Sync manager for handling OneDrive delta synchronization.
"""
import os
import json
import logging
import time
import traceback
from datetime import datetime
from onedrive_client import OneDriveClient
from config import STATE_FILE, FILE_TYPES_TO_EXCLUDE, PATHS_TO_EXCLUDE, SYNC_INTERVAL_MINUTES

class SyncManager:
    """
    Manages the synchronization process between OneDrive and local files.
    Implements delta sync to efficiently track and download only changed files.
    """
    def __init__(self, check_only=False, test_mode=False, max_files=None, target_folder=None, root_only=False):
        """
        Initialize the sync manager.

        Args:
            check_only (bool): If True, only check for changes without downloading
            test_mode (bool): If True, run in test mode with limited files
            max_files (int): Maximum number of files to download in test mode
            target_folder (str): Specific folder to sync
            root_only (bool): If True, only download files in the root (not in any folder)
        """
        self.client = OneDriveClient()
        self.state_file = STATE_FILE
        self.delta_link = None
        self.last_sync = None

        # Sync options
        self.check_only = check_only
        self.test_mode = test_mode
        self.max_files = max_files if test_mode else None
        self.target_folder = target_folder
        self.root_only = root_only
        self.files_processed = 0

        logging.debug(f"SyncManager initialized with options: check_only={check_only}, "
                     f"test_mode={test_mode}, max_files={max_files}, target_folder={target_folder}, "
                     f"root_only={root_only}")

        self.load_state()

    def load_state(self):
        """Load previous sync state including delta link."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.delta_link = state.get("delta_link")
                    self.last_sync = state.get("last_sync")
                    logging.info(f"Loaded sync state. Last sync: {self.last_sync}")
                    return True
            logging.info("No previous sync state found. Will perform full sync.")
            return False
        except Exception as e:
            logging.error(f"Error loading sync state: {str(e)}")
            return False

    def save_state(self):
        """Save current sync state."""
        try:
            state = {
                "delta_link": self.delta_link,
                "last_sync": datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
            logging.info("Saved sync state.")
        except Exception as e:
            logging.error(f"Error saving sync state: {str(e)}")

    def should_process_item(self, item):
        """
        Determine if an item should be processed based on exclusion rules.
        """
        # Skip deleted items (we'll handle them separately)
        if item.get('deleted'):
            return True

        # Check file extension exclusions
        name = item.get('name', '')
        if any(name.lower().endswith(ext.lower()) for ext in FILE_TYPES_TO_EXCLUDE):
            logging.info(f"Skipping excluded file type: {name}")
            return False

        # Check path exclusions
        parent_path = self.client._get_parent_path(item)
        full_path = os.path.join(parent_path, name)
        if any(excl_path in full_path for excl_path in PATHS_TO_EXCLUDE):
            logging.info(f"Skipping excluded path: {full_path}")
            return False

        return True

    def process_item(self, item):
        """
        Process a changed item (file or folder).
        """
        try:
            # Skip items that match exclusion rules
            if not self.should_process_item(item):
                return

            # Handle deleted items
            if item.get('deleted'):
                self.handle_deletion(item)
                return

            name = item.get('name', '')
            parent_path = self.client._get_parent_path(item)
            full_path = os.path.join(parent_path, name) if parent_path else name

            # Check if we're targeting a specific folder and this item is not in that folder
            if self.target_folder and not (
                full_path.startswith(self.target_folder) or
                parent_path.startswith(self.target_folder) or
                name == self.target_folder
            ):
                logging.debug(f"Skipping item not in target folder: {full_path}")
                return

            # Check if we only want root files and this item is in a folder
            if self.root_only:
                if parent_path:  # If parent_path is not empty, the item is not in the root
                    logging.debug(f"Skipping non-root item: {full_path}")
                    return
                logging.debug(f"Processing root item: {name}")

                # Skip folders if we only want root files
                if 'folder' in item:
                    logging.debug(f"Skipping folder in root-only mode: {name}")
                    return

            # Check if we've reached the maximum number of files in test mode
            if self.test_mode and self.max_files is not None and self.files_processed >= self.max_files:
                logging.debug(f"Skipping item due to max files limit: {name}")
                return

            # Handle folder
            if 'folder' in item:
                self.handle_folder(item)
            # Handle file
            elif 'file' in item:
                self.handle_file(item)
                # Increment the files processed counter if we're in test mode
                if self.test_mode:
                    self.files_processed += 1
                    logging.info(f"Processed {self.files_processed}/{self.max_files} files in test mode")
            else:
                logging.warning(f"Unknown item type: {name}")

        except Exception as e:
            logging.error(f"Error processing item {item.get('name', 'unknown')}: {str(e)}")

    def handle_folder(self, item):
        """
        Handle a folder item - create the folder locally if it doesn't exist.
        """
        try:
            name = item.get('name', '')
            parent_path = self.client._get_parent_path(item)
            folder_path = os.path.join(self.client.download_path, parent_path, name)

            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                logging.info(f"Created folder: {folder_path}")

        except Exception as e:
            logging.error(f"Error handling folder {item.get('name', 'unknown')}: {str(e)}")

    def handle_file(self, item):
        """
        Handle a file item - download the file.
        """
        try:
            name = item.get('name', '')
            parent_path = self.client._get_parent_path(item)
            file_path = os.path.join(self.client.download_path, parent_path, name)

            # Get file size for logging
            size_bytes = item.get('size', 0)
            size_mb = size_bytes / (1024 * 1024)
            size_display = f"{size_mb:.2f} MB" if size_bytes > 0 else "unknown size"

            # Check if file exists and compare modification times
            if os.path.exists(file_path):
                local_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                remote_mtime_str = item.get('lastModifiedDateTime')

                if remote_mtime_str:
                    remote_mtime = datetime.fromisoformat(remote_mtime_str.replace('Z', '+00:00'))

                    # Skip download if local file is newer or same age
                    if local_mtime >= remote_mtime:
                        logging.info(f"Skipping file (local copy is up-to-date): {name}")
                        return

            # In check-only mode, just log what would be downloaded
            if self.check_only:
                logging.info(f"Would download: {name} ({size_display})")
                return

            # In test mode, provide more detailed logging
            if self.test_mode:
                logging.info(f"Test mode - downloading file {self.files_processed+1}/{self.max_files}: {name} ({size_display})")
            else:
                logging.info(f"Downloading file: {name} ({size_display})")

            # Download the file (unless in check-only mode)
            self.client.download_file(item)

        except Exception as e:
            logging.error(f"Error handling file {item.get('name', 'unknown')}: {str(e)}")

    def handle_deletion(self, item):
        """
        Handle a deleted item - delete it locally if it exists.
        """
        try:
            # For deleted items, we need to use the ID to figure out what was deleted
            item_id = item.get('id')

            # This is tricky because we don't have the path anymore
            # We would need to maintain a mapping of item IDs to local paths
            # For simplicity, we'll log the deletion but not act on it
            logging.info(f"Item with ID {item_id} was deleted in OneDrive")

            # In a more complete implementation, you would:
            # 1. Maintain a database of item IDs to local paths
            # 2. Look up the local path for this ID
            # 3. Delete the local file or folder

        except Exception as e:
            logging.error(f"Error handling deletion for item ID {item.get('id', 'unknown')}: {str(e)}")

    def perform_sync(self):
        """
        Perform a delta sync with OneDrive.
        """
        try:
            # Reset counters
            self.files_processed = 0
            files_would_download = 0

            # Log sync mode
            if self.check_only:
                logging.info("Starting sync process in CHECK-ONLY mode (no downloads)...")
            elif self.test_mode:
                logging.info(f"Starting sync process in TEST mode (max {self.max_files} files)...")
                if self.target_folder:
                    logging.info(f"Targeting folder: {self.target_folder}")
            elif self.root_only:
                logging.info("Starting sync process in ROOT-ONLY mode (only files not in any folder)...")
            else:
                logging.info("Starting sync process...")

            # Get changes since last sync
            delta_response = self.client.get_delta(self.delta_link)

            # Process each changed item
            items = delta_response.get('value', [])
            total_items = len(items)
            logging.info(f"Found {total_items} changed items")

            # Count files and folders for reporting
            files_count = sum(1 for item in items if 'file' in item)
            folders_count = sum(1 for item in items if 'folder' in item)
            deleted_count = sum(1 for item in items if 'deleted' in item)

            logging.info(f"Changes include: {files_count} files, {folders_count} folders, {deleted_count} deletions")

            # Process items
            for i, item in enumerate(items):
                if i % 10 == 0:  # Log progress every 10 items
                    logging.info(f"Processing item {i+1}/{total_items}...")
                self.process_item(item)

            # Save the delta link for next sync
            if '@odata.deltaLink' in delta_response:
                self.delta_link = delta_response['@odata.deltaLink']
                self.save_state()

            # Log summary
            if self.check_only:
                logging.info(f"Sync completed successfully in CHECK-ONLY mode")
                logging.info(f"Would have downloaded {files_would_download} files")
            elif self.test_mode:
                logging.info(f"Sync completed successfully in TEST mode")
                logging.info(f"Downloaded {self.files_processed}/{self.max_files} files")
            elif self.root_only:
                logging.info(f"Sync completed successfully in ROOT-ONLY mode")
                logging.info(f"Downloaded {self.files_processed} files from the root directory")
            else:
                logging.info("Sync completed successfully")
                logging.info(f"Downloaded {self.files_processed} files")

            return True

        except Exception as e:
            logging.error(f"Error during sync: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            return False

    def run_continuous_sync(self):
        """
        Run the sync process continuously at specified intervals.
        """
        try:
            logging.info(f"Starting continuous sync (interval: {SYNC_INTERVAL_MINUTES} minutes)")

            while True:
                success = self.perform_sync()

                if success:
                    logging.info(f"Waiting {SYNC_INTERVAL_MINUTES} minutes until next sync...")
                else:
                    logging.warning(f"Sync failed. Will retry in {SYNC_INTERVAL_MINUTES} minutes...")

                # Sleep until next sync
                time.sleep(SYNC_INTERVAL_MINUTES * 60)

        except KeyboardInterrupt:
            logging.info("Sync process interrupted by user")
        except Exception as e:
            logging.error(f"Unexpected error in continuous sync: {str(e)}")

    def run_one_time_sync(self):
        """
        Run a one-time sync process.
        """
        return self.perform_sync()
