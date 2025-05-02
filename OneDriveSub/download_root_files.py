"""
Simplified script to download only files from the root of OneDrive.
This script doesn't use delta sync to avoid any issues with state files.
"""
import os
import sys
import json
import logging
import requests
import msal
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("root_download.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configuration
CLIENT_ID = "4a1aa1d5-c567-49d0-ad0b-cd957a47f842"  # Microsoft Graph Explorer client ID
AUTHORITY = "https://login.microsoftonline.com/common"  # Works for personal accounts
SCOPES = ["User.Read", "Files.Read", "Files.Read.All"]  # Scopes for file access
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DOWNLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

# Create downloads directory if it doesn't exist
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

def get_token():
    """Get an access token for Microsoft Graph API."""
    try:
        # Load token cache
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as file:
                cache.deserialize(file.read())
        
        # Create the MSAL public client application
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        # Try to get token from cache first
        accounts = app.get_accounts()
        if accounts:
            logging.info("Found account in cache, attempting to get token silently")
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result:
                logging.info("Successfully acquired token from cache")
                # Save cache
                if cache.has_state_changed:
                    with open(token_cache_path, "w") as file:
                        file.write(cache.serialize())
                return result['access_token']
        
        # If no token in cache or expired, try device code flow
        logging.info("No valid token in cache, attempting device code flow")
        flow = app.initiate_device_flow(scopes=SCOPES)
        
        if "user_code" in flow:
            # Print the message with the code for the user
            print("\n" + flow["message"])
            print("\nWaiting for you to complete the authentication in your browser...")
            
            # Try to open the verification URL automatically
            try:
                import webbrowser
                webbrowser.open(flow["verification_uri"])
            except:
                pass
            
            # Complete the flow by waiting for the user to enter the code
            result = app.acquire_token_by_device_flow(flow)
        else:
            # If device code flow fails, fall back to interactive login
            logging.info("Device code flow failed, attempting interactive login")
            print("\nYou will be redirected to your browser to sign in with your Microsoft account.")
            result = app.acquire_token_interactive(SCOPES)
        
        if "access_token" in result:
            logging.info("Successfully acquired token through interactive login")
            # Save cache
            if cache.has_state_changed:
                with open(token_cache_path, "w") as file:
                    file.write(cache.serialize())
            return result['access_token']
        else:
            error_description = result.get("error_description", "Unknown error")
            error = result.get("error", "Unknown error")
            logging.error(f"Authentication failed: {error} - {error_description}")
            raise Exception(f"Authentication failed: {error} - {error_description}")
    
    except Exception as e:
        logging.error(f"Error during authentication: {str(e)}")
        raise

def get_root_files():
    """Get all files in the root of OneDrive."""
    try:
        # Get token
        token = get_token()
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get items in the root folder
        logging.info("Getting items in the root folder...")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/root/children",
            headers=headers
        )
        response.raise_for_status()
        
        # Parse response
        items = response.json().get('value', [])
        
        # Filter for files only (not folders)
        files = [item for item in items if 'file' in item]
        folders = [item for item in items if 'folder' in item]
        
        logging.info(f"Found {len(files)} files and {len(folders)} folders in the root")
        
        return files
    
    except Exception as e:
        logging.error(f"Error getting root files: {str(e)}")
        raise

def download_file(file_item):
    """Download a file from OneDrive."""
    try:
        # Get token
        token = get_token()
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        name = file_item.get('name', 'unknown')
        file_id = file_item.get('id')
        
        # Get download URL
        logging.info(f"Getting download URL for file: {name}")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/items/{file_id}",
            headers=headers
        )
        response.raise_for_status()
        
        download_url = response.json().get('@microsoft.graph.downloadUrl')
        if not download_url:
            logging.error(f"Could not get download URL for file: {name}")
            return False
        
        # Download the file
        logging.info(f"Downloading file: {name}")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # Save the file
        file_path = os.path.join(DOWNLOAD_PATH, name)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logging.info(f"Downloaded: {file_path}")
        return True
    
    except Exception as e:
        logging.error(f"Error downloading file {file_item.get('name', 'unknown')}: {str(e)}")
        return False

def main():
    """Main function."""
    try:
        print("\n=== OneDrive Root Files Downloader ===\n")
        
        # Get all files in the root
        files = get_root_files()
        
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
                if download_file(file):
                    success_count += 1
            
            print(f"\nDownloaded {success_count} of {len(files)} files successfully.")
        
        elif choice == "2":
            # Download specific files
            indices = input("\nEnter file numbers to download (comma-separated, e.g., 1,3,5): ")
            try:
                indices = [int(idx.strip()) - 1 for idx in indices.split(",")]
                selected_files = [files[idx] for idx in indices if 0 <= idx < len(files)]
                
                print(f"\nDownloading {len(selected_files)} files...")
                success_count = 0
                for file in selected_files:
                    if download_file(file):
                        success_count += 1
                
                print(f"\nDownloaded {success_count} of {len(selected_files)} files successfully.")
            
            except Exception as e:
                print(f"Error parsing file numbers: {str(e)}")
        
        else:
            print("\nExiting without downloading any files.")
        
        print("\n=== Download Complete ===\n")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        logging.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()
