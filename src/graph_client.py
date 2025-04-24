"""
Microsoft Graph API client for accessing SharePoint/OneDrive files.
"""
import requests
import os
import json
from tqdm import tqdm
from .config import GRAPH_BASE_URL, DOWNLOAD_PATH
from .auth import GraphAuth

class GraphClient:
    """
    Client for interacting with Microsoft Graph API to access SharePoint/OneDrive files.
    """
    def __init__(self):
        """Initialize the Graph API client."""
        self.auth = GraphAuth()
        self.base_url = GRAPH_BASE_URL
        self.download_path = DOWNLOAD_PATH

    def _make_request(self, endpoint, method="GET", params=None, data=None):
        """Make a request to the Microsoft Graph API."""
        url = f"{self.base_url}/{endpoint}"
        headers = self.auth.get_headers()

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data
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
                json=data
            )

        # Raise exception for other errors
        response.raise_for_status()

        if response.content:
            return response.json()
        return None

    def get_drives(self):
        """Get available drives (OneDrive/SharePoint sites)."""
        try:
            # First try the personal account approach (OneDrive)
            return self._make_request("me/drive")
        except Exception as e:
            # If that fails, try the organizational approach
            try:
                return self._make_request("me/drives")
            except Exception as inner_e:
                # As a last resort, try to get just the default drive
                try:
                    drive = self._make_request("me/drive")
                    # Format it to match the expected structure
                    return {"value": [drive]}
                except Exception as final_e:
                    raise Exception(f"Failed to get drives: {str(final_e)}")

    def get_drive_items(self, drive_id, item_id="root"):
        """Get items in a drive or folder."""
        return self._make_request(f"drives/{drive_id}/items/{item_id}/children")

    def download_file(self, drive_id, item_id, file_path, relative_path=""):
        """Download a file from SharePoint/OneDrive."""
        # Get file metadata
        file_metadata = self._make_request(f"drives/{drive_id}/items/{item_id}")

        # Get download URL
        download_url = file_metadata.get("@microsoft.graph.downloadUrl")
        if not download_url:
            raise Exception(f"Could not get download URL for file: {file_path}")

        # Create local directory structure if it doesn't exist
        local_dir = os.path.join(self.download_path, relative_path)
        os.makedirs(local_dir, exist_ok=True)

        # Download the file
        local_file_path = os.path.join(local_dir, file_path)

        # Stream download with progress bar
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        file_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte

        print(f"Downloading: {file_path}")
        with open(local_file_path, 'wb') as f, tqdm(
            desc=file_path,
            total=file_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                size = f.write(data)
                bar.update(size)

        print(f"Downloaded: {local_file_path}")
        return local_file_path

    def download_folder(self, drive_id, item_id, folder_path, relative_path=""):
        """Download a folder and its contents recursively."""
        # Create local directory
        local_dir = os.path.join(self.download_path, relative_path, folder_path)
        os.makedirs(local_dir, exist_ok=True)

        # Get folder contents
        items = self.get_drive_items(drive_id, item_id)

        # Process each item
        for item in items.get("value", []):
            item_name = item.get("name")
            item_id = item.get("id")

            if "folder" in item:
                # Recursively download folder
                new_relative_path = os.path.join(relative_path, folder_path)
                self.download_folder(drive_id, item_id, item_name, new_relative_path)
            else:
                # Download file
                new_relative_path = os.path.join(relative_path, folder_path)
                self.download_file(drive_id, item_id, item_name, new_relative_path)

        return local_dir
