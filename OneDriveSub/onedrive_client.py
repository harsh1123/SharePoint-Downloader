"""
OneDrive client for interacting with Microsoft Graph API.
"""
import requests
import os
import json
import logging
import traceback
from urllib.parse import urlparse
from auth import OneDriveAuth
from config import GRAPH_BASE_URL, DOWNLOAD_PATH

class OneDriveClient:
    """
    Client for interacting with OneDrive via Microsoft Graph API.
    Uses interactive authentication for individual users.
    """
    def __init__(self):
        """Initialize the OneDrive client."""
        self.auth = OneDriveAuth()
        self.base_url = GRAPH_BASE_URL
        self.download_path = DOWNLOAD_PATH
        self.drive_id = None

    def _make_request(self, endpoint, method="GET", params=None, data=None, stream=False):
        """Make a request to the Microsoft Graph API."""
        url = f"{self.base_url}/{endpoint}"
        headers = self.auth.get_headers()

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                stream=stream
            )

            # Handle token expiration
            if response.status_code == 401:
                # Token expired, get a new one
                self.auth.access_token = None
                headers = self.auth.get_headers()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    stream=stream
                )

            # Raise exception for other errors
            response.raise_for_status()

            if method == "GET" and not stream and response.content:
                return response.json()
            return response

        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {str(e)}")
            raise

    def get_drive(self):
        """
        Get the user's OneDrive.
        """
        try:
            # For personal accounts, we use /me/drive
            response = self._make_request("me/drive")
            self.drive_id = response.get('id')

            if not self.drive_id:
                raise Exception("Could not get OneDrive ID")

            logging.info(f"Retrieved OneDrive ID: {self.drive_id}")
            return response

        except Exception as e:
            logging.error(f"Error getting OneDrive: {str(e)}")
            raise

    def get_drive_id(self):
        """
        Get the user's OneDrive ID.
        """
        if self.drive_id:
            return self.drive_id

        drive = self.get_drive()
        return self.drive_id

    def get_delta(self, delta_link=None):
        """
        Get changes since the last sync using delta query.
        If delta_link is provided, it will be used to get only changes since the last query.

        This method handles pagination automatically and returns a complete response with all items.
        """
        try:
            drive_id = self.get_drive_id()
            all_items = []
            final_response = None
            current_link = None

            # Log detailed information about the delta request
            if delta_link:
                logging.info("Using existing delta link for incremental sync")
                logging.debug(f"Delta link: {delta_link}")
                current_link = delta_link
            else:
                logging.info("No delta link provided. Performing full sync.")
                current_link = f"{self.base_url}/me/drive/root/delta"
                logging.debug(f"Using initial delta endpoint: {current_link}")

            # Process all pages of results
            page_count = 0
            while current_link:
                page_count += 1
                logging.info(f"Fetching delta page {page_count}...")

                # Make the request - handle full URLs or relative endpoints
                if current_link.startswith(self.base_url):
                    # It's a full URL, extract the endpoint
                    endpoint = current_link.replace(self.base_url + '/', '')
                    logging.debug(f"Extracted endpoint from link: {endpoint}")
                    response = self._make_request(endpoint)
                else:
                    # It's already an endpoint or a relative URL
                    logging.debug(f"Using link as endpoint: {current_link}")
                    response = self._make_request(current_link)

                if not response:
                    logging.warning(f"Received empty response for page {page_count}")
                    break

                # Get items from this page and add to our collection
                page_items = response.get('value', [])
                all_items.extend(page_items)
                logging.info(f"Page {page_count} contains {len(page_items)} items")

                # Save the final response for returning delta link
                final_response = response

                # Check for next page or delta link
                if '@odata.nextLink' in response:
                    current_link = response['@odata.nextLink']
                    logging.info(f"Found next page link. Will fetch page {page_count + 1}")
                    logging.debug(f"Next link: {current_link}")
                elif '@odata.deltaLink' in response:
                    # We've reached the last page, and we have a delta link
                    delta_link = response['@odata.deltaLink']
                    logging.info("Reached last page. Delta link found.")
                    logging.debug(f"Delta link: {delta_link}")
                    current_link = None  # Exit the loop
                else:
                    # No more pages and no delta link
                    logging.warning("No next page link or delta link found. This is unexpected.")
                    logging.debug(f"Response keys: {list(response.keys())}")
                    current_link = None  # Exit the loop

            # Create a combined response with all items
            if final_response:
                # Create a new response with all items
                combined_response = {
                    'value': all_items
                }

                # Copy over any odata properties
                for key in final_response:
                    if key.startswith('@odata.') and key != '@odata.nextLink':
                        combined_response[key] = final_response[key]

                logging.info(f"Completed delta query. Total items: {len(all_items)}")

                # Check for delta link in final response
                if '@odata.deltaLink' in final_response:
                    logging.info("Delta link found in final response")
                else:
                    logging.warning("No delta link found in final response. This may cause issues with incremental sync.")
                    logging.debug(f"Final response keys: {list(final_response.keys())}")

                return combined_response
            else:
                logging.warning("No valid response received from any page")
                return {'value': []}

        except Exception as e:
            logging.error(f"Error getting delta changes: {str(e)}")
            logging.debug(f"Stack trace: {traceback.format_exc()}")
            raise

    def get_items(self, item_id="root"):
        """
        Get items in a folder.
        """
        try:
            drive_id = self.get_drive_id()

            if item_id == "root":
                endpoint = f"me/drive/root/children"
            else:
                endpoint = f"me/drive/items/{item_id}/children"

            return self._make_request(endpoint)

        except Exception as e:
            logging.error(f"Error getting items: {str(e)}")
            raise

    def download_file(self, item):
        """
        Download a file from OneDrive.
        """
        try:
            # Get download URL
            download_url = item.get('@microsoft.graph.downloadUrl')
            if not download_url:
                file_id = item.get('id')

                # Get file metadata to get the download URL
                file_metadata = self._make_request(f"me/drive/items/{file_id}")
                download_url = file_metadata.get('@microsoft.graph.downloadUrl')

                if not download_url:
                    raise Exception(f"Could not get download URL for file: {item.get('name')}")

            # Get the relative path of the file
            parent_path = self._get_parent_path(item)
            file_name = item.get('name')

            # Create local directory structure if it doesn't exist
            local_dir = os.path.join(self.download_path, parent_path)
            os.makedirs(local_dir, exist_ok=True)

            # Download the file
            local_file_path = os.path.join(local_dir, file_name)

            # Stream download
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logging.info(f"Downloaded: {local_file_path}")
            return local_file_path

        except Exception as e:
            logging.error(f"Error downloading file {item.get('name')}: {str(e)}")
            raise

    def _get_parent_path(self, item):
        """
        Get the parent path of an item.
        """
        try:
            parent_reference = item.get('parentReference', {})
            path = parent_reference.get('path', '')
            name = item.get('name', 'unknown')

            # Log the raw path for debugging
            logging.debug(f"Raw parent path for '{name}': {path}")

            # The path is usually in the format "/drive/root:/path/to/parent"
            if ':' in path:
                path = path.split(':')[-1]
                logging.debug(f"After splitting at colon: {path}")

            # Remove leading slash
            path = path.lstrip('/')

            # Log whether this is a root item
            is_root = (path == '')
            logging.debug(f"Item '{name}' is {'in root' if is_root else 'not in root'} (path: '{path}')")

            return path

        except Exception as e:
            logging.error(f"Error getting parent path: {str(e)}")
            return ""
