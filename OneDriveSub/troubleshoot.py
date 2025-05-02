"""
Troubleshooting script for the OneDrive Sync Tool.
This script performs various tests to diagnose issues with the tool.
"""
import os
import sys
import json
import logging
import requests
import msal
import platform
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("troubleshoot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Import local modules
try:
    from config import CLIENT_ID, AUTHORITY, SCOPES, DOWNLOAD_PATH, STATE_FILE
    logging.info("Successfully imported configuration")
except ImportError as e:
    logging.error(f"Failed to import configuration: {str(e)}")
    sys.exit(1)

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)

def check_system_info():
    """Check system information."""
    print_section("System Information")
    
    # Python version
    python_version = sys.version
    print(f"Python version: {python_version}")
    logging.info(f"Python version: {python_version}")
    
    # Operating system
    os_info = platform.platform()
    print(f"Operating system: {os_info}")
    logging.info(f"Operating system: {os_info}")
    
    # Check for required modules
    required_modules = ["msal", "requests"]
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} module is installed")
            logging.info(f"{module} module is installed")
        except ImportError:
            print(f"❌ {module} module is NOT installed")
            logging.error(f"{module} module is NOT installed")
    
    # Check for token cache
    token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
    if os.path.exists(token_cache_path):
        print(f"✅ Token cache exists: {token_cache_path}")
        logging.info(f"Token cache exists: {token_cache_path}")
        
        # Check token cache size
        size = os.path.getsize(token_cache_path)
        print(f"   Token cache size: {size} bytes")
        logging.info(f"Token cache size: {size} bytes")
        
        # Check if token cache is valid JSON
        try:
            with open(token_cache_path, "r") as f:
                json.load(f)
            print(f"✅ Token cache is valid JSON")
            logging.info(f"Token cache is valid JSON")
        except json.JSONDecodeError:
            print(f"❌ Token cache is NOT valid JSON")
            logging.error(f"Token cache is NOT valid JSON")
    else:
        print(f"❌ Token cache does not exist")
        logging.warning(f"Token cache does not exist")
    
    # Check for sync state file
    if os.path.exists(STATE_FILE):
        print(f"✅ Sync state file exists: {STATE_FILE}")
        logging.info(f"Sync state file exists: {STATE_FILE}")
        
        # Check sync state file size
        size = os.path.getsize(STATE_FILE)
        print(f"   Sync state file size: {size} bytes")
        logging.info(f"Sync state file size: {size} bytes")
        
        # Check if sync state file is valid JSON
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                print(f"✅ Sync state file is valid JSON")
                logging.info(f"Sync state file is valid JSON")
                
                # Check for delta link
                if "delta_link" in state:
                    print(f"✅ Sync state contains delta link")
                    logging.info(f"Sync state contains delta link")
                else:
                    print(f"❌ Sync state does NOT contain delta link")
                    logging.warning(f"Sync state does NOT contain delta link")
                
                # Check for last sync time
                if "last_sync" in state:
                    last_sync = state["last_sync"]
                    print(f"✅ Last sync: {last_sync}")
                    logging.info(f"Last sync: {last_sync}")
                else:
                    print(f"❌ Sync state does NOT contain last sync time")
                    logging.warning(f"Sync state does NOT contain last sync time")
        except json.JSONDecodeError:
            print(f"❌ Sync state file is NOT valid JSON")
            logging.error(f"Sync state file is NOT valid JSON")
    else:
        print(f"❌ Sync state file does not exist")
        logging.warning(f"Sync state file does not exist")
    
    # Check for downloads directory
    if os.path.exists(DOWNLOAD_PATH):
        print(f"✅ Downloads directory exists: {DOWNLOAD_PATH}")
        logging.info(f"Downloads directory exists: {DOWNLOAD_PATH}")
        
        # Count files in downloads directory
        file_count = sum([len(files) for _, _, files in os.walk(DOWNLOAD_PATH)])
        print(f"   Files in downloads directory: {file_count}")
        logging.info(f"Files in downloads directory: {file_count}")
    else:
        print(f"❌ Downloads directory does not exist")
        logging.warning(f"Downloads directory does not exist")

def test_authentication():
    """Test authentication with Microsoft Graph API."""
    print_section("Authentication Test")
    
    try:
        # Load token cache
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as f:
                cache.deserialize(f.read())
        
        # Create the MSAL public client application
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        # Try to get token from cache first
        accounts = app.get_accounts()
        if accounts:
            print(f"✅ Found {len(accounts)} account(s) in cache")
            logging.info(f"Found {len(accounts)} account(s) in cache")
            
            for i, account in enumerate(accounts):
                print(f"   Account {i+1}: {account.get('username')}")
                logging.info(f"Account {i+1}: {account.get('username')}")
            
            print("Attempting to get token silently...")
            logging.info("Attempting to get token silently...")
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            
            if result:
                print(f"✅ Successfully acquired token from cache")
                logging.info(f"Successfully acquired token from cache")
                token = result['access_token']
                token_preview = token[:10] + "..." + token[-10:]
                print(f"   Token preview: {token_preview}")
                logging.info(f"Token preview: {token_preview}")
                
                # Test the token with a simple Graph API call
                print("Testing token with Graph API call...")
                logging.info("Testing token with Graph API call...")
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
                
                response = requests.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"✅ Token works for /me endpoint")
                    logging.info(f"Token works for /me endpoint")
                    user_data = response.json()
                    print(f"   User: {user_data.get('displayName')} ({user_data.get('userPrincipalName')})")
                    logging.info(f"User: {user_data.get('displayName')} ({user_data.get('userPrincipalName')})")
                else:
                    print(f"❌ Token doesn't work for /me endpoint: {response.status_code}")
                    logging.error(f"Token doesn't work for /me endpoint: {response.status_code} - {response.text}")
                
                # Test with OneDrive
                print("Testing token with OneDrive...")
                logging.info("Testing token with OneDrive...")
                
                response = requests.get(
                    "https://graph.microsoft.com/v1.0/me/drive",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"✅ Token works for OneDrive")
                    logging.info(f"Token works for OneDrive")
                    drive_data = response.json()
                    print(f"   Drive: {drive_data.get('name')} (ID: {drive_data.get('id')})")
                    logging.info(f"Drive: {drive_data.get('name')} (ID: {drive_data.get('id')})")
                    
                    # Get root folder
                    print("Testing access to root folder...")
                    logging.info("Testing access to root folder...")
                    
                    response = requests.get(
                        "https://graph.microsoft.com/v1.0/me/drive/root/children",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        print(f"✅ Successfully accessed root folder")
                        logging.info(f"Successfully accessed root folder")
                        items = response.json().get("value", [])
                        print(f"   Items in root folder: {len(items)}")
                        logging.info(f"Items in root folder: {len(items)}")
                        
                        # List a few items
                        for i, item in enumerate(items[:5]):
                            item_type = "Folder" if "folder" in item else "File"
                            print(f"   - {item.get('name')} ({item_type})")
                            logging.info(f"Item {i+1}: {item.get('name')} ({item_type})")
                        
                        if len(items) > 5:
                            print(f"   - ... and {len(items) - 5} more items")
                            logging.info(f"... and {len(items) - 5} more items")
                    else:
                        print(f"❌ Failed to access root folder: {response.status_code}")
                        logging.error(f"Failed to access root folder: {response.status_code} - {response.text}")
                else:
                    print(f"❌ Token doesn't work for OneDrive: {response.status_code}")
                    logging.error(f"Token doesn't work for OneDrive: {response.status_code} - {response.text}")
            else:
                print(f"❌ Failed to acquire token silently")
                logging.error(f"Failed to acquire token silently")
                print("You may need to re-authenticate. Try deleting the .token_cache file and running the sync tool again.")
        else:
            print(f"❌ No accounts found in cache")
            logging.warning(f"No accounts found in cache")
            print("You need to authenticate first. Run the sync tool to authenticate.")
    
    except Exception as e:
        print(f"❌ Error during authentication test: {str(e)}")
        logging.error(f"Error during authentication test: {str(e)}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")

def test_delta_sync():
    """Test delta sync functionality."""
    print_section("Delta Sync Test")
    
    if not os.path.exists(STATE_FILE):
        print(f"❌ Sync state file does not exist: {STATE_FILE}")
        logging.warning(f"Sync state file does not exist: {STATE_FILE}")
        print("You need to run the sync tool first to create a sync state.")
        return
    
    try:
        # Load sync state
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        
        if "delta_link" not in state:
            print(f"❌ Sync state does not contain delta link")
            logging.warning(f"Sync state does not contain delta link")
            print("You need to run the sync tool first to create a delta link.")
            return
        
        delta_link = state["delta_link"]
        print(f"✅ Found delta link in sync state")
        logging.info(f"Found delta link in sync state")
        
        # Get token
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as f:
                cache.deserialize(f.read())
        
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        accounts = app.get_accounts()
        if not accounts:
            print(f"❌ No accounts found in cache")
            logging.warning(f"No accounts found in cache")
            print("You need to authenticate first. Run the sync tool to authenticate.")
            return
        
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result:
            print(f"❌ Failed to acquire token silently")
            logging.error(f"Failed to acquire token silently")
            print("You may need to re-authenticate. Try deleting the .token_cache file and running the sync tool again.")
            return
        
        token = result['access_token']
        print(f"✅ Successfully acquired token")
        logging.info(f"Successfully acquired token")
        
        # Test delta sync
        print("Testing delta sync...")
        logging.info("Testing delta sync...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        # Extract the endpoint from the delta link
        endpoint = delta_link.replace("https://graph.microsoft.com/v1.0/", "")
        
        response = requests.get(
            delta_link,
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully called delta endpoint")
            logging.info(f"Successfully called delta endpoint")
            
            delta_response = response.json()
            items = delta_response.get("value", [])
            print(f"   Changes since last sync: {len(items)}")
            logging.info(f"Changes since last sync: {len(items)}")
            
            # List a few changed items
            for i, item in enumerate(items[:5]):
                if "deleted" in item:
                    print(f"   - {item.get('id')} (Deleted)")
                    logging.info(f"Changed item {i+1}: {item.get('id')} (Deleted)")
                else:
                    item_type = "Folder" if "folder" in item else "File"
                    print(f"   - {item.get('name')} ({item_type})")
                    logging.info(f"Changed item {i+1}: {item.get('name')} ({item_type})")
            
            if len(items) > 5:
                print(f"   - ... and {len(items) - 5} more changes")
                logging.info(f"... and {len(items) - 5} more changes")
            
            # Check for new delta link
            if "@odata.deltaLink" in delta_response:
                print(f"✅ Received new delta link")
                logging.info(f"Received new delta link")
            else:
                print(f"❌ No new delta link received")
                logging.warning(f"No new delta link received")
        else:
            print(f"❌ Failed to call delta endpoint: {response.status_code}")
            logging.error(f"Failed to call delta endpoint: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"❌ Error during delta sync test: {str(e)}")
        logging.error(f"Error during delta sync test: {str(e)}")
        logging.debug(f"Stack trace: {traceback.format_exc()}")

def main():
    """Main function."""
    print_section("OneDrive Sync Tool Troubleshooter")
    print("This script will help diagnose issues with the OneDrive Sync Tool.")
    print("Detailed logs will be saved to troubleshoot.log")
    
    # Check system information
    check_system_info()
    
    # Test authentication
    test_authentication()
    
    # Test delta sync
    test_delta_sync()
    
    print("\nTroubleshooting complete. Check troubleshoot.log for detailed information.")

if __name__ == "__main__":
    main()
