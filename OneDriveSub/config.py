"""
Configuration settings for the OneDrive Sync Tool for individual users.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent
PARENT_DIR = BASE_DIR.parent

# Local file system settings
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
# Keep the state file in the same directory as the script
STATE_FILE = os.path.join(BASE_DIR, "onedrive_sync_state.json")
LOG_FILE = os.path.join(BASE_DIR, "sync.log")
DEBUG_LOG_FILE = os.path.join(BASE_DIR, "debug.log")

# Logging settings
LOG_LEVEL = "DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create downloads directory if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Microsoft Graph API settings
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Microsoft Authentication settings for individual users
# Using a public client ID that works with personal accounts
CLIENT_ID = "4a1aa1d5-c567-49d0-ad0b-cd957a47f842"  # Microsoft Graph Explorer client ID
AUTHORITY = "https://login.microsoftonline.com/common"  # Works for personal accounts
SCOPES = ["User.Read", "Files.Read", "Files.Read.All"]  # Scopes for file access

# Sync settings
SYNC_INTERVAL_MINUTES = 60  # How often to sync in minutes when running continuously
FILE_TYPES_TO_EXCLUDE = []  # File extensions to exclude, e.g., ['.tmp', '.bak']
PATHS_TO_EXCLUDE = []  # Paths to exclude, e.g., ['Documents/Archive']
