"""
SharePoint-only downloader that completely ignores OneDrive.
This script attempts to access SharePoint sites directly through the sites API.
"""
import os
import sys
import json
import requests
from src.graph_client import GraphClient
from src.config import DOWNLOAD_PATH, GRAPH_BASE_URL

def print_separator():
    """Print a separator line."""
    print("-" * 80)

def display_menu(options):
    """Display a menu of options and get user selection."""
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    while True:
        try:
            choice = int(input("\nEnter your choice (number): "))
            if 1 <= choice <= len(options):
                return choice
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")

def get_sharepoint_sites(client):
    """
    Get SharePoint sites using various API endpoints.
    This tries multiple approaches to find SharePoint sites.
    """
    sites = []
    
    # Approach 1: Try to get sites directly
    try:
        print("Attempting to fetch SharePoint sites directly...")
        response = client._make_request("sites")
        if "value" in response:
            sites.extend(response.get("value", []))
    except Exception as e:
        print(f"Could not fetch sites directly: {str(e)}")
    
    # Approach 2: Try to get followed sites
    try:
        print("Attempting to fetch followed SharePoint sites...")
        response = client._make_request("me/followedSites")
        if "value" in response:
            sites.extend(response.get("value", []))
    except Exception as e:
        print(f"Could not fetch followed sites: {str(e)}")
    
    # Approach 3: Try to get root site
    try:
        print("Attempting to fetch root SharePoint site...")
        response = client._make_request("sites/root")
        if "id" in response:
            sites.append(response)
    except Exception as e:
        print(f"Could not fetch root site: {str(e)}")
    
    # Approach 4: Try to get specific tenant sites
    try:
        print("Attempting to fetch tenant SharePoint sites...")
        # This is a common pattern for SharePoint site URLs
        tenant_name = input("Enter your Microsoft 365 tenant name (e.g., 'contoso' for contoso.sharepoint.com): ")
        if tenant_name:
            response = client._make_request(f"sites/{tenant_name}.sharepoint.com:/sites")
            if "value" in response:
                sites.extend(response.get("value", []))
    except Exception as e:
        print(f"Could not fetch tenant sites: {str(e)}")
    
    return sites

def get_sharepoint_drives(client, sites):
    """Get drives from SharePoint sites."""
    drives = []
    
    for site in sites:
        site_id = site.get("id")
        site_name = site.get("displayName", "Unnamed Site")
        site_url = site.get("webUrl", "")
        
        print(f"Fetching drives for site: {site_name} ({site_url})")
        
        try:
            response = client._make_request(f"sites/{site_id}/drives")
            site_drives = response.get("value", [])
            
            # Add site information to each drive for better context
            for drive in site_drives:
                drive["siteName"] = site_name
                drive["siteUrl"] = site_url
            
            drives.extend(site_drives)
        except Exception as e:
            print(f"Could not fetch drives for site {site_name}: {str(e)}")
    
    return drives

def browse_sharepoint_drives(client):
    """Browse SharePoint drives and let user select one."""
    print("\nSearching for SharePoint sites and drives...")
    
    # Get SharePoint sites
    sites = get_sharepoint_sites(client)
    
    if not sites:
        print("\nNo SharePoint sites found. Your account might not have access to SharePoint.")
        print("This is common for personal Microsoft accounts that aren't part of an organization.")
        print("You would need a Microsoft 365 work or school account to access SharePoint sites.")
        return None, None
    
    print(f"\nFound {len(sites)} SharePoint sites.")
    
    # Get drives from the sites
    drives = get_sharepoint_drives(client, sites)
    
    if not drives:
        print("\nNo document libraries found in the SharePoint sites.")
        print("The sites might be empty or you might not have sufficient permissions.")
        return None, None
    
    print(f"\nFound {len(drives)} SharePoint document libraries.")
    print("\nAvailable SharePoint document libraries:")
    
    drive_options = []
    for drive in drives:
        name = drive.get('name', 'Unnamed Library')
        site_name = drive.get('siteName', 'Unnamed Site')
        drive_options.append(f"{name} (Site: {site_name})")
    
    if len(drive_options) == 1:
        print(f"Found 1 SharePoint library: {drive_options[0]}")
        selected_drive = drives[0]
        return selected_drive.get("id"), selected_drive.get("name")
    else:
        choice = display_menu(drive_options)
        selected_drive = drives[choice - 1]
        return selected_drive.get("id"), selected_drive.get("name")

def browse_items(client, drive_id, item_id="root", path=""):
    """Browse items in a drive or folder."""
    try:
        items_response = client.get_drive_items(drive_id, item_id)
        items = items_response.get("value", [])
        
        if not items:
            print("\nNo items found in this location.")
            return
        
        # Separate folders and files
        folders = [item for item in items if "folder" in item]
        files = [item for item in items if "folder" not in item]
        
        # Sort alphabetically
        folders.sort(key=lambda x: x.get("name", "").lower())
        files.sort(key=lambda x: x.get("name", "").lower())
        
        # Combine for display
        all_items = folders + files
        
        print(f"\nItems in {path or 'root'}:")
        item_options = []
        
        for item in all_items:
            name = item.get("name", "")
            size = item.get("size", 0)
            item_type = "📁 " if "folder" in item else "📄 "
            
            # Format size for files
            if "folder" not in item:
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                item_options.append(f"{item_type}{name} ({size_str})")
            else:
                item_options.append(f"{item_type}{name}")
        
        # Add navigation options
        item_options.append("⬆️ Go back")
        item_options.append("💾 Download current folder")
        item_options.append("🏠 Return to main menu")
        item_options.append("❌ Exit")
        
        choice = display_menu(item_options)
        
        if choice <= len(all_items):
            # Selected an item
            selected_item = all_items[choice - 1]
            selected_name = selected_item.get("name", "")
            selected_id = selected_item.get("id", "")
            
            if "folder" in selected_item:
                # Navigate into folder
                new_path = f"{path}/{selected_name}" if path else selected_name
                browse_items(client, drive_id, selected_id, new_path)
            else:
                # Download file
                print(f"\nDownloading {selected_name}...")
                relative_path = path.lstrip("/") if path else ""
                client.download_file(drive_id, selected_id, selected_name, relative_path)
                print(f"\nFile downloaded to: {os.path.join(DOWNLOAD_PATH, relative_path, selected_name)}")
                
                # Return to the same folder
                browse_items(client, drive_id, item_id, path)
        
        elif choice == len(all_items) + 1:
            # Go back
            if path:
                # Go up one level
                parent_path = "/".join(path.split("/")[:-1])
                parent_id = "root"
                
                if parent_path:
                    # Need to get the parent folder's ID
                    parent_parts = parent_path.split("/")
                    current_id = "root"
                    
                    for part in parent_parts:
                        items_response = client.get_drive_items(drive_id, current_id)
                        items = items_response.get("value", [])
                        for item in items:
                            if item.get("name") == part and "folder" in item:
                                current_id = item.get("id")
                                break
                    
                    parent_id = current_id
                
                browse_items(client, drive_id, parent_id, parent_path)
            else:
                # At root, go back to drive selection
                main()
        
        elif choice == len(all_items) + 2:
            # Download current folder
            print(f"\nDownloading entire folder: {path or 'root'}...")
            folder_name = path.split("/")[-1] if path else "root"
            relative_path = "/".join(path.split("/")[:-1]) if path else ""
            relative_path = relative_path.lstrip("/")
            
            client.download_folder(drive_id, item_id, folder_name, relative_path)
            print(f"\nFolder downloaded to: {os.path.join(DOWNLOAD_PATH, relative_path, folder_name)}")
            
            # Return to the same folder
            browse_items(client, drive_id, item_id, path)
        
        elif choice == len(all_items) + 3:
            # Return to main menu
            main()
        
        else:
            # Exit
            print("\nExiting application. Downloaded files are in the 'downloads' folder.")
            sys.exit(0)
    
    except Exception as e:
        print(f"Error browsing items: {str(e)}")
        input("\nPress Enter to continue...")
        main()

def download_all_sharepoint(client):
    """Download all SharePoint content automatically."""
    print("\nSearching for SharePoint sites and drives...")
    
    # Get SharePoint sites
    sites = get_sharepoint_sites(client)
    
    if not sites:
        print("\nNo SharePoint sites found. Your account might not have access to SharePoint.")
        print("This is common for personal Microsoft accounts that aren't part of an organization.")
        print("You would need a Microsoft 365 work or school account to access SharePoint sites.")
        return
    
    print(f"\nFound {len(sites)} SharePoint sites.")
    
    # Get drives from the sites
    drives = get_sharepoint_drives(client, sites)
    
    if not drives:
        print("\nNo document libraries found in the SharePoint sites.")
        print("The sites might be empty or you might not have sufficient permissions.")
        return
    
    print(f"\nFound {len(drives)} SharePoint document libraries. Downloading all content...")
    
    # Process each SharePoint drive
    for drive in drives:
        drive_id = drive.get("id")
        drive_name = drive.get("name", "Unnamed Library")
        site_name = drive.get("siteName", "Unnamed Site")
        
        print(f"\nProcessing SharePoint library: {drive_name} (Site: {site_name})")
        
        # Create a folder for this drive
        drive_folder = os.path.join(DOWNLOAD_PATH, site_name, drive_name)
        os.makedirs(drive_folder, exist_ok=True)
        
        # Download all content from the drive
        download_folder_recursive(client, drive_id, "root", "", os.path.join(site_name, drive_name))
    
    print("\nDownload completed successfully!")
    print(f"All SharePoint files have been downloaded to: {os.path.abspath(DOWNLOAD_PATH)}")

def download_folder_recursive(client, drive_id, folder_id, path, drive_path):
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
                folder_path = os.path.join(DOWNLOAD_PATH, drive_path, path, item_name)
                os.makedirs(folder_path, exist_ok=True)
                
                # Download its contents
                download_folder_recursive(client, drive_id, item_id, current_path, drive_path)
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
                local_folder = os.path.join(DOWNLOAD_PATH, drive_path, path)
                os.makedirs(local_folder, exist_ok=True)
                
                # Download the file
                client.download_file(drive_id, item_id, item_name, os.path.join(drive_path, path))
    
    except Exception as e:
        print(f"Error processing {path or 'root'}: {str(e)}")

def main():
    """Main function to run the application."""
    print_separator()
    print("SharePoint-Only File Downloader".center(80))
    print_separator()
    print("This application connects to Microsoft 365 and allows you to download")
    print("files from SharePoint sites ONLY (completely ignoring OneDrive).")
    print_separator()
    
    try:
        # Initialize the Graph client
        client = GraphClient()
        
        # Show menu options
        print("\nWhat would you like to do?")
        options = [
            "Browse SharePoint sites and download files interactively",
            "Download all SharePoint content automatically",
            "Exit"
        ]
        
        choice = display_menu(options)
        
        if choice == 1:
            # Browse and download interactively
            drive_id, drive_name = browse_sharepoint_drives(client)
            
            if drive_id:
                print(f"\nSelected SharePoint library: {drive_name}")
                
                # Browse items in the selected drive
                browse_items(client, drive_id)
            else:
                print("\nNo SharePoint library selected. Exiting.")
        
        elif choice == 2:
            # Download all SharePoint content
            download_all_sharepoint(client)
        
        else:
            # Exit
            print("\nExiting application.")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
