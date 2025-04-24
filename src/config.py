"""
Configuration settings for the SharePoint File Downloader.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv is not installed, continue without it
    pass

# Microsoft Graph API settings
# Get client ID from environment variable or use the hardcoded value
CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", "92745f6f-1015-4d78-96c7-7f2d5fab8d9d")
AUTHORITY = "https://login.microsoftonline.com/common"  # Works for both personal and work accounts
SCOPE = ["User.Read", "Files.Read", "Files.Read.All", "Sites.Read.All"]  # Scopes for file access

# Local file system settings
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
TOKEN_CACHE_FILE = os.path.join(BASE_DIR, ".token_cache")

# Create downloads directory if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# API endpoints
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
