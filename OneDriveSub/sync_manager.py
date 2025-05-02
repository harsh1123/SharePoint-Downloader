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
    def __init__(self, check_only=False, test_mode=False, max_files=None, target_folder=None,
                 root_only=False, force_full_sync=False, force_save_state=False):
        """
        Initialize the sync manager.

        Args:
            check_only (bool): If True, only check for changes without downloading
            test_mode (bool): If True, run in test mode with limited files
            max_files (int): Maximum number of files to download in test mode
            target_folder (str): Specific folder to sync
            root_only (bool): If True, only download files in the root (not in any folder)
            force_full_sync (bool): If True, ignore existing delta link and perform full sync
            force_save_state (bool): If True, force saving the state file after sync
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
        self.force_full_sync = force_full_sync
        self.force_save_state = force_save_state
        self.files_processed = 0

        logging.debug(f"SyncManager initialized with options: check_only={check_only}, "
                     f"test_mode={test_mode}, max_files={max_files}, target_folder={target_folder}, "
                     f"root_only={root_only}, force_full_sync={force_full_sync}, "
                     f"force_save_state={force_save_state}")

        self.load_state()

    def load_state(self):
        """Load previous sync state including delta link."""
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
            logging.debug(f"State contents: {state}")

            # Check if force_full_sync is enabled
            if self.force_full_sync:
                logging.info("Force full sync enabled. Ignoring existing delta link.")
                self.delta_link = None
            else:
                # Get delta link from state
                self.delta_link = state.get("delta_link")

                # Validate delta link
                if self.delta_link:
                    if not isinstance(self.delta_link, str) or not self.delta_link.startswith("http"):
                        logging.warning(f"Invalid delta link format: {self.delta_link}")
                        self.delta_link = None

            # Get last sync time
            self.last_sync = state.get("last_sync")

            # Log sync status
            if self.last_sync:
                logging.info(f"Last sync: {self.last_sync}")
            else:
                logging.info("No previous sync time found")

            # Log delta link status
            if self.delta_link:
                logging.info("Delta link found. Will perform incremental sync.")
                logging.debug(f"Delta link: {self.delta_link}")
            else:
                logging.info("No valid delta link found. Will perform full sync.")

            return True

        except Exception as e:
            logging.error(f"Error loading sync state: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            logging.info("Will perform full sync due to error.")
            return False

    def show_state(self):
        """Show the current sync state."""
        try:
            print("\n=== Current Sync State ===\n")

            # Check if state file exists
            if os.path.exists(self.state_file):
                print(f"State file: {os.path.abspath(self.state_file)}")
                file_size = os.path.getsize(self.state_file)
                print(f"File size: {file_size} bytes")

                # Load and display state
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                    # Show last sync time
                    last_sync = state.get("last_sync", "Never")
                    print(f"Last sync: {last_sync}")

                    # Show delta link
                    delta_link = state.get("delta_link", "None")
                    if delta_link:
                        print(f"Delta link: {delta_link[:50]}...{delta_link[-50:] if len(delta_link) > 100 else delta_link[50:]}")
                    else:
                        print("Delta link: None")

                    # Show other state information if available
                    for key, value in state.items():
                        if key not in ["delta_link", "last_sync"]:
                            print(f"{key}: {value}")
            else:
                print(f"No state file found at: {os.path.abspath(self.state_file)}")
                print("A full sync will be performed on the next run.")

            # Show token cache information
            token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
            if os.path.exists(token_cache_path):
                print(f"\nToken cache: {token_cache_path}")
                file_size = os.path.getsize(token_cache_path)
                print(f"Token cache size: {file_size} bytes")
            else:
                print("\nNo token cache found. Authentication will be required on next run.")

            # Show download directory information
            download_path = self.client.download_path
            if os.path.exists(download_path):
                print(f"\nDownload directory: {os.path.abspath(download_path)}")
                file_count = sum([len(files) for _, _, files in os.walk(download_path)])
                print(f"Files in download directory: {file_count}")
            else:
                print(f"\nDownload directory does not exist: {os.path.abspath(download_path)}")

            print("\n=== End of Sync State ===\n")

        except Exception as e:
            print(f"Error showing sync state: {str(e)}")
            logging.error(f"Error showing sync state: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")

    def save_state(self):
        """Save current sync state."""
        try:
            # Log the state file path
            logging.info(f"Attempting to save sync state to: {os.path.abspath(self.state_file)}")

            # Check if delta_link exists
            if not self.delta_link:
                logging.warning("No delta link to save. Creating a dummy delta link.")
                self.delta_link = f"https://graph.microsoft.com/v1.0/me/drive/root/delta?token=dummy_{int(time.time())}"
                logging.debug(f"Created dummy delta link: {self.delta_link}")

            # Create state object
            state = {
                "delta_link": self.delta_link,
                "last_sync": datetime.now().isoformat(),
                "version": "1.0",  # Add version for future compatibility
                "sync_type": "root_only" if self.root_only else "full"
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
                    json.dump({"delta_link": self.delta_link, "last_sync": datetime.now().isoformat()}, f)
                logging.info("Fallback save succeeded")
            except Exception as e2:
                logging.error(f"Fallback save also failed: {str(e2)}")

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
                # Log the item details for debugging
                item_type = "Folder" if 'folder' in item else "File"
                logging.debug(f"Checking root-only for {item_type}: {name}")
                logging.debug(f"Parent path: '{parent_path}'")
                logging.debug(f"Full path: '{full_path}'")

                # Check if the item is in the root
                if parent_path:  # If parent_path is not empty, the item is not in the root
                    logging.debug(f"Skipping non-root item: {full_path}")
                    return

                logging.info(f"Found root item: {name} ({item_type})")

                # Skip folders if we only want root files
                if 'folder' in item:
                    logging.debug(f"Skipping folder in root-only mode: {name}")
                    return

                # Log the item details for debugging
                size_bytes = item.get('size', 0)
                size_mb = size_bytes / (1024 * 1024)
                size_display = f"{size_mb:.2f} MB" if size_bytes > 0 else "unknown size"
                logging.info(f"Root file details: {name} ({size_display})")

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

    def list_root_files(self):
        """
        List all files in the root of OneDrive.
        This is useful for debugging root-only mode.
        """
        try:
            logging.info("Listing all files in the root of OneDrive...")

            # Get items in the root folder
            response = self.client._make_request("me/drive/root/children")
            items = response.get('value', [])

            # Count files and folders
            root_files = [item for item in items if 'file' in item]
            root_folders = [item for item in items if 'folder' in item]

            logging.info(f"Found {len(root_files)} files and {len(root_folders)} folders in the root")

            # List all files in the root
            if root_files:
                logging.info("Files in the root:")
                for i, file in enumerate(root_files):
                    name = file.get('name', 'unknown')
                    size_bytes = file.get('size', 0)
                    size_mb = size_bytes / (1024 * 1024)
                    size_display = f"{size_mb:.2f} MB" if size_bytes > 0 else "unknown size"
                    logging.info(f"  {i+1}. {name} ({size_display})")
            else:
                logging.info("No files found in the root")

            return root_files
        except Exception as e:
            logging.error(f"Error listing root files: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            return []

    def download_root_files_directly(self):
        """
        Download files directly from the root of OneDrive.
        This is a fallback method if delta sync doesn't find any root files.
        """
        try:
            logging.info("Downloading files directly from the root of OneDrive...")

            # Get all files in the root
            root_files = self.list_root_files()

            if not root_files:
                logging.info("No root files found to download")
                return

            # Download each file
            files_downloaded = 0
            for file in root_files:
                # Skip if we've reached the maximum number of files in test mode
                if self.test_mode and self.max_files is not None and files_downloaded >= self.max_files:
                    logging.info(f"Reached maximum number of files ({self.max_files})")
                    break

                name = file.get('name', 'unknown')
                size_bytes = file.get('size', 0)
                size_mb = size_bytes / (1024 * 1024)
                size_display = f"{size_mb:.2f} MB" if size_bytes > 0 else "unknown size"

                # In check-only mode, just log what would be downloaded
                if self.check_only:
                    logging.info(f"Would download root file: {name} ({size_display})")
                    continue

                # Download the file
                logging.info(f"Downloading root file: {name} ({size_display})")
                self.client.download_file(file)
                files_downloaded += 1
                self.files_processed += 1

            logging.info(f"Direct download completed. Downloaded {files_downloaded} root files.")

        except Exception as e:
            logging.error(f"Error downloading root files directly: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            return

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
                # List root files for debugging
                self.list_root_files()
            else:
                logging.info("Starting sync process...")

            # Log delta link status
            if self.delta_link:
                logging.info(f"Using existing delta link from previous sync")
                logging.debug(f"Delta link: {self.delta_link}")
            else:
                logging.info(f"No delta link found. Performing full sync.")

            # Get changes since last sync
            logging.info("Requesting changes from OneDrive...")
            delta_response = self.client.get_delta(self.delta_link)

            # Check if we got a valid response
            if not delta_response or 'value' not in delta_response:
                logging.error("Invalid delta response received")
                logging.debug(f"Response: {delta_response}")
                return False

            # Check for deltaLink in response
            if '@odata.deltaLink' in delta_response:
                new_delta_link = delta_response['@odata.deltaLink']
                logging.info("Received new delta link from OneDrive")
                logging.debug(f"New delta link: {new_delta_link}")
                self.delta_link = new_delta_link
            else:
                logging.warning("No delta link received in response")
                logging.debug(f"Response keys: {list(delta_response.keys())}")

                # Try to create a delta link for next time
                if self.force_save_state:
                    logging.info("Force save state enabled. Will create a dummy delta link.")
                    self.delta_link = f"https://graph.microsoft.com/v1.0/me/drive/root/delta?token=dummy_{int(time.time())}"
                    logging.debug(f"Created dummy delta link: {self.delta_link}")

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
            logging.info("Checking for delta link in response...")
            if '@odata.deltaLink' in delta_response:
                logging.info("Delta link found in response. Saving state...")
                # Delta link was already set earlier, just save the state
                self.save_state()
            else:
                logging.warning("No delta link found in response.")
                # Log the response keys for debugging
                logging.debug(f"Response keys: {list(delta_response.keys())}")

                # If force_save_state is enabled, save the state anyway
                if self.force_save_state:
                    logging.info("Force save state enabled. Creating a dummy delta link and saving state...")
                    # Create a dummy delta link
                    self.delta_link = f"https://graph.microsoft.com/v1.0/me/drive/root/delta?token=dummy_{int(time.time())}"
                    self.save_state()
                else:
                    logging.warning("State will not be saved. Use --force-save-state to override this.")

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

                # If no files were downloaded and this is the first sync, try direct download
                if self.files_processed == 0 and not self.delta_link:
                    logging.info("No root files found via delta sync. Trying direct download...")
                    self.download_root_files_directly()
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

    def create_test_state_file(self):
        """
        Create a test state file with a dummy delta link.
        This is useful for debugging state file issues.
        """
        try:
            logging.info("Creating test state file...")

            # Create a dummy delta link
            dummy_delta_link = "https://graph.microsoft.com/v1.0/me/drive/root/delta?token=test_token"
            self.delta_link = dummy_delta_link

            # Save the state
            self.save_state()

            # Verify the file was created
            if os.path.exists(self.state_file):
                logging.info(f"Test state file created successfully at: {os.path.abspath(self.state_file)}")
                return True
            else:
                logging.error(f"Failed to create test state file")
                return False

        except Exception as e:
            logging.error(f"Error creating test state file: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            return False

    def run_one_time_sync(self):
        """
        Run a one-time sync process.
        """
        return self.perform_sync()
