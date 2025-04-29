"""
Sync manager for handling SharePoint delta synchronization.
"""
import os
import json
import logging
import time
from datetime import datetime
from sharepoint_client import SharePointClient
from config import STATE_FILE, FILE_TYPES_TO_EXCLUDE, PATHS_TO_EXCLUDE, SYNC_INTERVAL_MINUTES

class SyncManager:
    """
    Manages the synchronization process between SharePoint and local files.
    Implements delta sync to efficiently track and download only changed files.
    """
    def __init__(self):
        """Initialize the sync manager."""
        self.client = SharePointClient()
        self.state_file = STATE_FILE
        self.delta_link = None
        self.last_sync = None
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
            item_id = item.get('id')

            # Handle folder
            if 'folder' in item:
                self.handle_folder(item)
            # Handle file
            elif 'file' in item:
                self.handle_file(item)
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

            # Download the file
            logging.info(f"Downloading file: {name}")
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
            logging.info(f"Item with ID {item_id} was deleted in SharePoint")

            # In a more complete implementation, you would:
            # 1. Maintain a database of item IDs to local paths
            # 2. Look up the local path for this ID
            # 3. Delete the local file or folder

        except Exception as e:
            logging.error(f"Error handling deletion for item ID {item.get('id', 'unknown')}: {str(e)}")

    def perform_sync(self):
        """
        Perform a delta sync with SharePoint.
        """
        try:
            logging.info("Starting sync process...")

            # Get changes since last sync
            delta_response = self.client.get_delta(self.delta_link)

            # Process each changed item
            items = delta_response.get('value', [])
            logging.info(f"Found {len(items)} changed items")

            for item in items:
                self.process_item(item)

            # Save the delta link for next sync
            if '@odata.deltaLink' in delta_response:
                self.delta_link = delta_response['@odata.deltaLink']
                self.save_state()

            logging.info("Sync completed successfully")
            return True

        except Exception as e:
            logging.error(f"Error during sync: {str(e)}")
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
