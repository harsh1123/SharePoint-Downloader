"""
Manual sync manager for handling SharePoint synchronization without using delta API.
This implementation uses a local state file to track file changes.
"""
import os
import json
import logging
import time
import traceback
from datetime import datetime
from sharepoint_client import SharePointClient
from config import STATE_FILE, FILE_TYPES_TO_EXCLUDE, PATHS_TO_EXCLUDE, SYNC_INTERVAL_MINUTES

class ManualSyncManager:
    """
    Manages the synchronization process between SharePoint and local files.
    Uses a manual state tracking approach instead of delta sync API.
    """
    def __init__(self, check_only=False):
        """
        Initialize the sync manager.

        Args:
            check_only (bool): If True, only check for changes without downloading
        """
        self.client = SharePointClient()
        self.state_file = STATE_FILE
        self.file_state = {}
        self.last_sync = None
        self.check_only = check_only
        self.files_processed = 0

        logging.debug(f"ManualSyncManager initialized with options: check_only={check_only}")
        self.load_state()

    def load_state(self):
        """Load previous sync state including file metadata."""
        try:
            # Check if state file exists
            if not os.path.exists(self.state_file):
                logging.info(f"No state file found at: {os.path.abspath(self.state_file)}")
                logging.info("Will perform full sync.")
                return False

            # Check if state file is empty
            if os.path.getsize(self.state_file) == 0:
                logging.warning(f"State file exists but is empty: {os.path.abspath(self.state_file)}")
                logging.info("Will perform full sync.")
                return False

            # Try to load the state file
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"State file contains invalid JSON: {str(e)}")

                # Try to load backup if it exists
                backup_file = f"{self.state_file}.bak"
                if os.path.exists(backup_file):
                    logging.info(f"Attempting to load backup state file: {backup_file}")
                    try:
                        with open(backup_file, 'r') as f:
                            state = json.load(f)
                        logging.info("Successfully loaded backup state file")
                    except Exception as e2:
                        logging.error(f"Failed to load backup state file: {str(e2)}")
                        logging.info("Will perform full sync.")
                        return False
                else:
                    logging.info("No backup state file found. Will perform full sync.")
                    return False

            # Log the loaded state
            logging.info(f"Loaded sync state from: {os.path.abspath(self.state_file)}")
            
            # Get file state from state
            self.file_state = state.get("files", {})
            
            # Get last sync time
            self.last_sync = state.get("last_sync")

            # Log sync status
            if self.last_sync:
                logging.info(f"Last sync: {self.last_sync}")
                logging.info(f"Found {len(self.file_state)} files in state")
            else:
                logging.info("No previous sync time found")

            return True

        except Exception as e:
            logging.error(f"Error loading sync state: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            logging.info("Will perform full sync due to error.")
            return False

    def save_state(self):
        """Save current sync state."""
        try:
            # Log the state file path
            logging.info(f"Attempting to save sync state to: {os.path.abspath(self.state_file)}")

            # Create state object
            state = {
                "files": self.file_state,
                "last_sync": datetime.now().isoformat(),
                "version": "1.0"  # Add version for future compatibility
            }

            # Ensure directory exists
            state_dir = os.path.dirname(self.state_file)
            if state_dir and not os.path.exists(state_dir):
                logging.info(f"Creating directory for state file: {state_dir}")
                os.makedirs(state_dir, exist_ok=True)

            # First write to a temporary file, then rename to avoid corruption
            temp_file = f"{self.state_file}.tmp"
            logging.debug(f"Writing state to temporary file: {temp_file}")

            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)  # Use indentation for readability

            # Verify the temp file was created
            if not os.path.exists(temp_file):
                logging.error(f"Failed to create temporary state file at: {temp_file}")
                return

            # Rename the temp file to the actual state file
            if os.path.exists(self.state_file):
                # Create a backup of the existing state file
                backup_file = f"{self.state_file}.bak"
                try:
                    os.replace(self.state_file, backup_file)
                    logging.debug(f"Created backup of existing state file: {backup_file}")
                except Exception as e:
                    logging.warning(f"Could not create backup of state file: {str(e)}")

            # Now rename the temp file to the actual state file
            os.replace(temp_file, self.state_file)

            # Verify the file was created
            if os.path.exists(self.state_file):
                file_size = os.path.getsize(self.state_file)
                logging.info(f"Successfully saved sync state. File size: {file_size} bytes")

                # Read back the file to verify it's valid JSON
                try:
                    with open(self.state_file, 'r') as f:
                        json.load(f)
                    logging.debug("Verified state file contains valid JSON")
                except json.JSONDecodeError:
                    logging.error("State file contains invalid JSON!")
            else:
                logging.error(f"Failed to create state file at: {self.state_file}")

        except Exception as e:
            logging.error(f"Error saving sync state: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")

            # Try one more time with a simpler approach
            try:
                logging.info("Trying fallback method to save state...")
                with open(self.state_file, 'w') as f:
                    json.dump({"files": self.file_state, "last_sync": datetime.now().isoformat()}, f)
                logging.info("Fallback save succeeded")
            except Exception as e2:
                logging.error(f"Fallback save also failed: {str(e2)}")

    def should_process_item(self, item):
        """
        Determine if an item should be processed based on exclusion rules.
        """
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
        Process an item (file or folder).
        """
        try:
            # Skip items that match exclusion rules
            if not self.should_process_item(item):
                return

            name = item.get('name', '')
            parent_path = self.client._get_parent_path(item)
            full_path = os.path.join(parent_path, name) if parent_path else name

            # Handle folder
            if 'folder' in item:
                self.handle_folder(item)
            # Handle file
            elif 'file' in item:
                self.handle_file(item)
                self.files_processed += 1
            else:
                logging.warning(f"Unknown item type: {name}")

        except Exception as e:
            logging.error(f"Error processing item {item.get('name', 'unknown')}: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")

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
            logging.debug(f"Stack trace: {traceback.format_exc()}")

    def handle_file(self, item):
        """
        Handle a file item - download the file if it's new or modified.
        """
        try:
            # Get file metadata
            file_id = item.get('id')
            name = item.get('name', '')
            parent_path = self.client._get_parent_path(item)
            file_path = os.path.join(self.client.download_path, parent_path, name)
            remote_mtime_str = item.get('lastModifiedDateTime')
            size_bytes = item.get('size', 0)
            
            # Format size for display
            size_mb = size_bytes / (1024 * 1024)
            size_display = f"{size_mb:.2f} MB" if size_bytes > 0 else "unknown size"
            
            # Create a unique path key for the state file
            path_key = os.path.join(parent_path, name).replace('\\', '/')
            
            # Check if we need to download this file
            need_download = False
            
            # If the file is in our state
            if path_key in self.file_state:
                stored_info = self.file_state[path_key]
                stored_mtime = stored_info.get('lastModifiedDateTime')
                stored_size = stored_info.get('size', 0)
                
                # If the remote file is newer or different size, download it
                if remote_mtime_str and remote_mtime_str != stored_mtime:
                    logging.info(f"File has been modified: {name}")
                    need_download = True
                elif size_bytes != stored_size:
                    logging.info(f"File size has changed: {name}")
                    need_download = True
                else:
                    logging.info(f"File is unchanged: {name}")
            else:
                # File is not in our state, so it's new
                logging.info(f"New file found: {name}")
                need_download = True
            
            # Check if the local file exists and matches what we expect
            if os.path.exists(file_path) and not need_download:
                local_size = os.path.getsize(file_path)
                if local_size != size_bytes:
                    logging.info(f"Local file size ({local_size}) differs from remote ({size_bytes}): {name}")
                    need_download = True
            
            # If the local file doesn't exist, we need to download
            if not os.path.exists(file_path):
                need_download = True
            
            # In check-only mode, just log what would be downloaded
            if self.check_only:
                if need_download:
                    logging.info(f"Would download: {name} ({size_display})")
                return
            
            # Download the file if needed
            if need_download:
                logging.info(f"Downloading file: {name} ({size_display})")
                
                # Download the file
                self.client.download_file(item)
                
                # Update the state with the new file info
                self.file_state[path_key] = {
                    'id': file_id,
                    'name': name,
                    'lastModifiedDateTime': remote_mtime_str,
                    'size': size_bytes,
                    'path': path_key
                }
            else:
                logging.info(f"Skipping file (up-to-date): {name}")

        except Exception as e:
            logging.error(f"Error handling file {item.get('name', 'unknown')}: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")

    def get_all_files_recursive(self, folder_id="root", path=""):
        """
        Get all files recursively from SharePoint.
        
        Args:
            folder_id (str): The folder ID to start from
            path (str): The current path (for logging)
            
        Returns:
            list: List of file items
        """
        all_items = []
        try:
            # Get items in the current folder
            drive_id = self.client.get_drive_id()
            site_id = self.client.get_site_id()
            
            if folder_id == "root":
                endpoint = f"sites/{site_id}/drives/{drive_id}/root/children"
            else:
                endpoint = f"sites/{site_id}/drives/{drive_id}/items/{folder_id}/children"
                
            response = self.client._make_request(endpoint)
            items = response.get('value', [])
            
            # Process each item
            for item in items:
                # If it's a file, add it to our list
                if 'file' in item:
                    all_items.append(item)
                
                # If it's a folder, process it recursively
                elif 'folder' in item:
                    folder_id = item.get('id')
                    folder_name = item.get('name', '')
                    new_path = os.path.join(path, folder_name)
                    
                    # Get items in this folder
                    folder_items = self.get_all_files_recursive(folder_id, new_path)
                    all_items.extend(folder_items)
            
            return all_items
            
        except Exception as e:
            logging.error(f"Error getting files from {path or 'root'}: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            return all_items

    def perform_sync(self):
        """
        Perform a sync with SharePoint using manual state tracking.
        """
        try:
            # Reset counters
            self.files_processed = 0

            # Log sync mode
            if self.check_only:
                logging.info("Starting sync process in CHECK-ONLY mode (no downloads)...")
            else:
                logging.info("Starting sync process...")

            # Get all files recursively
            items = self.get_all_files_recursive()
            
            # Log what we found
            total_items = len(items)
            logging.info(f"Found {total_items} files to process")
            
            # Process each item
            for i, item in enumerate(items):
                if i % 10 == 0:  # Log progress every 10 items
                    logging.info(f"Processing item {i+1}/{total_items}...")
                self.process_item(item)
            
            # Save the state file
            self.save_state()
            
            # Log summary
            if self.check_only:
                logging.info(f"Sync completed successfully in CHECK-ONLY mode")
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
            logging.debug(f"Stack trace: {traceback.format_exc()}")

    def run_one_time_sync(self):
        """
        Run a one-time sync process.
        """
        return self.perform_sync()
