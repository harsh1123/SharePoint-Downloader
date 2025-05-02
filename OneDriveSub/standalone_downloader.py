"""
Standalone OneDrive root files downloader.
This script is completely self-contained and doesn't depend on any other modules.
"""
import os
import sys
import json
import time
import requests
import webbrowser
from datetime import datetime

try:
    import msal
except ImportError:
    print("MSAL library not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "msal"])
    import msal

# Configuration
CLIENT_ID = "4a1aa1d5-c567-49d0-ad0b-cd957a47f842"  # Microsoft Graph Explorer client ID
AUTHORITY = "https://login.microsoftonline.com/common"  # Works for personal accounts
SCOPES = ["User.Read", "Files.Read", "Files.Read.All"]  # Scopes for file access
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Create necessary directories
script_dir = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(script_dir, "downloads")
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# Set up simple logging
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def get_token():
    """Get an access token for Microsoft Graph API."""
    try:
        log("Starting authentication process")
        
        # Load token cache
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(script_dir, ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as file:
                cache.deserialize(file.read())
            log(f"Token cache loaded from: {token_cache_path}")
        else:
            log("No token cache found. Will perform interactive authentication.")
        
        # Create the MSAL public client application
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        # Try to get token from cache first
        accounts = app.get_accounts()
        if accounts:
            log(f"Found {len(accounts)} account(s) in cache")
            
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                log("Successfully acquired token from cache")
                
                # Save cache
                if cache.has_state_changed:
                    with open(token_cache_path, "w") as file:
                        file.write(cache.serialize())
                
                return result['access_token']
        
        # If no token in cache or expired, try device code flow
        log("No valid token in cache, attempting device code flow")
        flow = app.initiate_device_flow(scopes=SCOPES)
        
        if "user_code" in flow:
            # Print the message with the code for the user
            print("\n" + flow["message"])
            print("\nWaiting for you to complete the authentication in your browser...")
            
            # Try to open the verification URL automatically
            try:
                webbrowser.open(flow["verification_uri"])
            except:
                log("Could not open browser automatically", "WARNING")
            
            # Complete the flow by waiting for the user to enter the code
            result = app.acquire_token_by_device_flow(flow)
        else:
            # If device code flow fails, fall back to interactive login
            log("Device code flow failed, attempting interactive login")
            print("\nYou will be redirected to your browser to sign in with your Microsoft account.")
            result = app.acquire_token_interactive(SCOPES)
        
        if "access_token" in result:
            log("Successfully acquired token through interactive login")
            
            # Save cache
            if cache.has_state_changed:
                with open(token_cache_path, "w") as file:
                    file.write(cache.serialize())
                log(f"Token cache saved to: {token_cache_path}")
            
            return result['access_token']
        else:
            error_description = result.get("error_description", "Unknown error")
            error = result.get("error", "Unknown error")
            log(f"Authentication failed: {error} - {error_description}", "ERROR")
            return None
    
    except Exception as e:
        log(f"Error during authentication: {str(e)}", "ERROR")
        import traceback
        log(f"Stack trace: {traceback.format_exc()}", "ERROR")
        return None

def get_root_files(token):
    """Get all files in the root of OneDrive."""
    try:
        log("Getting files from the root of OneDrive")
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get items in the root folder
        log("Sending request to Microsoft Graph API")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/root/children",
            headers=headers
        )
        
        # Check for errors
        if response.status_code != 200:
            log(f"API request failed with status code: {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return []
        
        # Parse response
        items = response.json().get('value', [])
        
        # Filter for files only (not folders)
        files = [item for item in items if 'file' in item]
        folders = [item for item in items if 'folder' in item]
        
        log(f"Found {len(files)} files and {len(folders)} folders in the root")
        
        return files
    
    except Exception as e:
        log(f"Error getting root files: {str(e)}", "ERROR")
        import traceback
        log(f"Stack trace: {traceback.format_exc()}", "ERROR")
        return []

def download_file(token, file_item):
    """Download a file from OneDrive."""
    try:
        name = file_item.get('name', 'unknown')
        file_id = file_item.get('id')
        size = file_item.get('size', 0)
        size_mb = size / (1024 * 1024)
        
        log(f"Downloading file: {name} ({size_mb:.2f} MB)")
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get download URL
        log(f"Getting download URL for file: {name}")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/items/{file_id}",
            headers=headers
        )
        
        # Check for errors
        if response.status_code != 200:
            log(f"Failed to get download URL. Status code: {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return False
        
        download_url = response.json().get('@microsoft.graph.downloadUrl')
        if not download_url:
            log(f"Could not get download URL for file: {name}", "ERROR")
            return False
        
        # Download the file
        log(f"Starting download of file: {name}")
        response = requests.get(download_url, stream=True)
        
        # Check for errors
        if response.status_code != 200:
            log(f"Failed to download file. Status code: {response.status_code}", "ERROR")
            return False
        
        # Save the file
        file_path = os.path.join(DOWNLOAD_PATH, name)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify the file was downloaded
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            log(f"Successfully downloaded file: {file_path} ({file_size} bytes)")
            return True
        else:
            log(f"Failed to save downloaded file: {file_path}", "ERROR")
            return False
    
    except Exception as e:
        log(f"Error downloading file {name}: {str(e)}", "ERROR")
        import traceback
        log(f"Stack trace: {traceback.format_exc()}", "ERROR")
        return False

def main():
    """Main function."""
    try:
        print("\n=== Standalone OneDrive Root Files Downloader ===\n")
        
        # Get authentication token
        token = get_token()
        if not token:
            print("Authentication failed. Cannot proceed.")
            return
        
        # Get all files in the root
        files = get_root_files(token)
        
        if not files:
            print("No files found in the root of your OneDrive.")
            return
        
        # Print list of files
        print(f"\nFound {len(files)} files in the root of your OneDrive:")
        for i, file in enumerate(files):
            name = file.get('name', 'unknown')
            size = file.get('size', 0)
            size_mb = size / (1024 * 1024)
            print(f"{i+1}. {name} ({size_mb:.2f} MB)")
        
        # Ask user if they want to download all files
        print("\nOptions:")
        print("1. Download all files")
        print("2. Download specific files")
        print("3. Exit without downloading")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            # Download all files
            print(f"\nDownloading all {len(files)} files...")
            success_count = 0
            for file in files:
                if download_file(token, file):
                    success_count += 1
            
            print(f"\nDownloaded {success_count} of {len(files)} files successfully.")
            print(f"Files are saved in: {os.path.abspath(DOWNLOAD_PATH)}")
        
        elif choice == "2":
            # Download specific files
            indices = input("\nEnter file numbers to download (comma-separated, e.g., 1,3,5): ")
            try:
                indices = [int(idx.strip()) - 1 for idx in indices.split(",")]
                selected_files = [files[idx] for idx in indices if 0 <= idx < len(files)]
                
                print(f"\nDownloading {len(selected_files)} files...")
                success_count = 0
                for file in selected_files:
                    if download_file(token, file):
                        success_count += 1
                
                print(f"\nDownloaded {success_count} of {len(selected_files)} files successfully.")
                print(f"Files are saved in: {os.path.abspath(DOWNLOAD_PATH)}")
            
            except Exception as e:
                print(f"Error parsing file numbers: {str(e)}")
        
        else:
            print("\nExiting without downloading any files.")
        
        print("\n=== Download Complete ===\n")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
