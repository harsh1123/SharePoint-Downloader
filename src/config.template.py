"""
Configuration settings for the SharePoint File Downloader.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Microsoft Graph API settings
# Get client ID from environment variable or use a placeholder
CLIENT_ID = os.getenv("GRAPH_CLIENT_ID", "YOUR_CLIENT_ID_HERE")  # Replace with your client ID from Azure Portal
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
