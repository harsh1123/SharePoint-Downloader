"""
Configuration settings for the Organizational SharePoint Sync Tool.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent

# Local file system settings
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
STATE_FILE = os.path.join(BASE_DIR, "sync_state.json")
LOG_FILE = os.path.join(BASE_DIR, "sync.log")

# Create downloads directory if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Microsoft Graph API settings
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# SharePoint credentials
# These should be set in a .env file or environment variables in production
TENANT_ID = os.environ.get("SHAREPOINT_TENANT_ID", "your_tenant_id")
CLIENT_ID = os.environ.get("SHAREPOINT_CLIENT_ID", "your_client_id")
CLIENT_SECRET = os.environ.get("SHAREPOINT_CLIENT_SECRET", "your_client_secret")
CLIENT_SECRET_ID = os.environ.get("SHAREPOINT_CLIENT_SECRET_ID", "your_client_secret_id")
SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "your_sharepoint_site_url")

# Sync settings
SYNC_INTERVAL_MINUTES = 60  # How often to sync in minutes when running continuously
FILE_TYPES_TO_EXCLUDE = []  # File extensions to exclude, e.g., ['.tmp', '.bak']
PATHS_TO_EXCLUDE = []  # Paths to exclude, e.g., ['Shared Documents/Archive']
