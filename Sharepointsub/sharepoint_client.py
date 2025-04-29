"""
SharePoint client for interacting with Microsoft Graph API.
"""
import requests
import os
import json
import logging
from urllib.parse import urlparse
from .auth import SharePointAuth
from .config import GRAPH_BASE_URL, SITE_URL, DOWNLOAD_PATH

class SharePointClient:
    """
    Client for interacting with SharePoint via Microsoft Graph API.
    Uses client credentials flow for authentication.
    """
    def __init__(self):
        """Initialize the SharePoint client."""
        self.auth = SharePointAuth()
        self.base_url = GRAPH_BASE_URL
        self.site_url = SITE_URL
        self.download_path = DOWNLOAD_PATH
        self.site_id = None
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
    
    def get_site_id(self):
        """
        Get the site ID from the site URL.
        This is needed for subsequent API calls.
        """
        if self.site_id:
            return self.site_id
        
        try:
            # Parse the site URL to extract the host and path
            parsed_url = urlparse(self.site_url)
            host = parsed_url.netloc
            path = parsed_url.path
            
            # If the URL is like https://contoso.sharepoint.com/sites/sitename
            if '/sites/' in self.site_url:
                site_name = path.split('/sites/')[1].split('/')[0]
                endpoint = f"sites/{host}:/sites/{site_name}"
            # If the URL is like https://contoso.sharepoint.com
            else:
                endpoint = f"sites/{host}"
            
            response = self._make_request(endpoint)
            self.site_id = response.get('id')
            
            if not self.site_id:
                raise Exception(f"Could not get site ID for {self.site_url}")
            
            logging.info(f"Retrieved site ID: {self.site_id}")
            return self.site_id
        
        except Exception as e:
            logging.error(f"Error getting site ID: {str(e)}")
            raise
    
    def get_drive_id(self):
        """
        Get the default document library drive ID.
        This is typically 'Shared Documents' in SharePoint.
        """
        if self.drive_id:
            return self.drive_id
        
        try:
            site_id = self.get_site_id()
            response = self._make_request(f"sites/{site_id}/drives")
            
            drives = response.get('value', [])
            if not drives:
                raise Exception(f"No drives found for site {self.site_url}")
            
            # Usually the first drive is the default document library
            self.drive_id = drives[0].get('id')
            
            if not self.drive_id:
                raise Exception(f"Could not get drive ID for site {self.site_url}")
            
            logging.info(f"Retrieved drive ID: {self.drive_id}")
            return self.drive_id
        
        except Exception as e:
            logging.error(f"Error getting drive ID: {str(e)}")
            raise
    
    def get_delta(self, delta_link=None):
        """
        Get changes since the last sync using delta query.
        If delta_link is provided, it will be used to get only changes since the last query.
        """
        try:
            site_id = self.get_site_id()
            drive_id = self.get_drive_id()
            
            if delta_link:
                endpoint = delta_link.replace(self.base_url + '/', '')
            else:
                endpoint = f"sites/{site_id}/drives/{drive_id}/root/delta"
            
            return self._make_request(endpoint)
        
        except Exception as e:
            logging.error(f"Error getting delta changes: {str(e)}")
            raise
    
    def download_file(self, item):
        """
        Download a file from SharePoint.
        """
        try:
            # Get download URL
            download_url = item.get('@microsoft.graph.downloadUrl')
            if not download_url:
                file_id = item.get('id')
                drive_id = self.get_drive_id()
                
                # Get file metadata to get the download URL
                file_metadata = self._make_request(f"drives/{drive_id}/items/{file_id}")
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
            
            # The path is usually in the format "/drives/{drive-id}/root:/path/to/parent"
            if ':' in path:
                path = path.split(':')[-1]
            
            # Remove leading slash
            path = path.lstrip('/')
            
            return path
        
        except Exception as e:
            logging.error(f"Error getting parent path: {str(e)}")
            return ""
