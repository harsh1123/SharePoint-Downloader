"""
Main entry point for the SharePoint File Downloader application.
"""
import os
import sys
from src.graph_client import GraphClient
from src.config import DOWNLOAD_PATH

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

def list_drives(client):
    """List available drives and let user select one."""
    print("\nFetching available drives (OneDrive/SharePoint sites)...")

    try:
        drives_response = client.get_drives()

        # Handle both single drive and multiple drives responses
        if "value" in drives_response:
            drives = drives_response.get("value", [])
        else:
            # Single drive response (typical for personal accounts)
            drives = [drives_response]

        if not drives:
            print("No drives found. Make sure your account has access to OneDrive or SharePoint.")
            return None, None

        print("\nAvailable drives:")
        drive_options = []

        for drive in drives:
            name = drive.get('name', 'Personal Drive')
            drive_type = drive.get('driveType', 'personal')
            drive_options.append(f"{name} ({drive_type})")

        if len(drive_options) == 1:
            print(f"Found 1 drive: {drive_options[0]}")
            selected_drive = drives[0]
            return selected_drive.get("id"), selected_drive.get("name", "Personal Drive")
        else:
            choice = display_menu(drive_options)
            selected_drive = drives[choice - 1]
            return selected_drive.get("id"), selected_drive.get("name")

    except Exception as e:
        print(f"Error listing drives: {str(e)}")
        return None, None

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

def main():
    """Main function to run the application."""
    print_separator()
    print("SharePoint File Downloader".center(80))
    print_separator()
    print("This application connects to Microsoft 365 and allows you to download")
    print("files from SharePoint and OneDrive for Business.")
    print_separator()

    try:
        # Initialize the Graph client
        client = GraphClient()

        # List drives and let user select one
        drive_id, drive_name = list_drives(client)

        if drive_id:
            print(f"\nSelected drive: {drive_name}")

            # Browse items in the selected drive
            browse_items(client, drive_id)
        else:
            print("\nNo drive selected. Exiting.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
