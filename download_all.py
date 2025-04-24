"""
Script to download all files from SharePoint/OneDrive automatically.
"""
import os
import sys
from src.graph_client import GraphClient
from src.config import DOWNLOAD_PATH

def download_all_files():
    """Download all files from the user's OneDrive/SharePoint."""
    print("=" * 80)
    print("SharePoint/OneDrive Automatic Downloader".center(80))
    print("=" * 80)
    print("This script will download ALL files from your OneDrive/SharePoint.")
    print("Files will be saved to the 'downloads' folder.")
    print("=" * 80)
    
    # Initialize the Graph client
    try:
        client = GraphClient()
        
        # Get available drives
        print("\nFetching available drives...")
        drives_response = client.get_drives()
        
        # Handle both single drive and multiple drives responses
        if "value" in drives_response:
            drives = drives_response.get("value", [])
        else:
            # Single drive response (typical for personal accounts)
            drives = [drives_response]
        
        if not drives:
            print("No drives found. Make sure your account has access to OneDrive or SharePoint.")
            return
        
        # Process each drive
        for drive in drives:
            drive_id = drive.get("id")
            drive_name = drive.get("name", "Personal Drive")
            drive_type = drive.get("driveType", "personal")
            
            print(f"\nProcessing drive: {drive_name} ({drive_type})")
            
            # Create a folder for this drive
            drive_folder = os.path.join(DOWNLOAD_PATH, drive_name)
            os.makedirs(drive_folder, exist_ok=True)
            
            # Download all content from the drive
            download_folder_recursive(client, drive_id, "root", "", drive_name)
            
        print("\nDownload completed successfully!")
        print(f"All files have been downloaded to: {os.path.abspath(DOWNLOAD_PATH)}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        input("\nPress Enter to exit...")

def download_folder_recursive(client, drive_id, folder_id, path, drive_name):
    """Recursively download a folder and all its contents."""
    try:
        # Get items in the current folder
        items_response = client.get_drive_items(drive_id, folder_id)
        items = items_response.get("value", [])
        
        if not items:
            print(f"No items found in {path or 'root'}")
            return
        
        # Process each item
        for item in items:
            item_name = item.get("name", "")
            item_id = item.get("id", "")
            
            # Build the current path for display
            current_path = f"{path}/{item_name}" if path else item_name
            
            if "folder" in item:
                # It's a folder - process recursively
                print(f"Processing folder: {current_path}")
                
                # Create the folder locally
                folder_path = os.path.join(DOWNLOAD_PATH, drive_name, path, item_name)
                os.makedirs(folder_path, exist_ok=True)
                
                # Download its contents
                download_folder_recursive(client, drive_id, item_id, current_path, drive_name)
            else:
                # It's a file - download it
                size = item.get("size", 0)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                
                print(f"Downloading file: {current_path} ({size_str})")
                
                # Prepare the local path
                local_folder = os.path.join(DOWNLOAD_PATH, drive_name, path)
                os.makedirs(local_folder, exist_ok=True)
                
                # Download the file
                client.download_file(drive_id, item_id, item_name, os.path.join(drive_name, path))
                
    except Exception as e:
        print(f"Error processing {path or 'root'}: {str(e)}")

if __name__ == "__main__":
    download_all_files()
