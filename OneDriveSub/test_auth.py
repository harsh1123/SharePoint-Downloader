"""
Simple script to test authentication with Microsoft Graph API.
"""
import os
import sys
import msal
import requests
import json

# Microsoft Graph API settings
CLIENT_ID = "4a1aa1d5-c567-49d0-ad0b-cd957a47f842"  # Microsoft Graph Explorer client ID
AUTHORITY = "https://login.microsoftonline.com/common"  # Works for personal accounts
SCOPES = ["User.Read", "Files.Read", "Files.Read.All"]  # Scopes for file access
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

def clear_token_cache():
    """Clear the token cache file."""
    token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
    if os.path.exists(token_cache_path):
        os.remove(token_cache_path)
        print(f"Token cache cleared: {token_cache_path}")
    else:
        print("No token cache found.")

def test_authentication():
    """Test authentication with Microsoft Graph API."""
    try:
        print("\n=== Testing Authentication ===\n")
        
        # Load token cache
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as file:
                cache.deserialize(file.read())
            print(f"Token cache loaded from: {token_cache_path}")
        else:
            print("No token cache found. Will perform interactive authentication.")
        
        # Create the MSAL public client application
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        # Try to get token from cache first
        accounts = app.get_accounts()
        if accounts:
            print(f"Found {len(accounts)} account(s) in cache.")
            for i, account in enumerate(accounts):
                print(f"  Account {i+1}: {account.get('username')}")
            
            print("\nAttempting to get token silently...")
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            
            if result:
                print("✅ Successfully acquired token from cache.")
                token = result['access_token']
                token_preview = token[:10] + "..." + token[-10:]
                print(f"Token preview: {token_preview}")
                
                # Test the token with a simple Graph API call
                print("\nTesting token with Graph API call to /me...")
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json"
                }
                
                response = requests.get(
                    f"{GRAPH_BASE_URL}/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"✅ Token works! User: {user_data.get('displayName')} ({user_data.get('userPrincipalName')})")
                else:
                    print(f"❌ Token doesn't work. Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                
                # Save cache
                if cache.has_state_changed:
                    with open(token_cache_path, "w") as file:
                        file.write(cache.serialize())
                    print(f"Token cache updated.")
                
                return True
            else:
                print("❌ Failed to acquire token silently. Token might be expired.")
        else:
            print("No accounts found in cache.")
        
        # If no token in cache or expired, try device code flow
        print("\nAttempting device code flow...")
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
            print("\nDevice code flow failed. Attempting interactive login...")
            print("You will be redirected to your browser to sign in with your Microsoft account.")
            result = app.acquire_token_interactive(SCOPES)
        
        if "access_token" in result:
            print("\n✅ Successfully acquired token through interactive login.")
            token = result['access_token']
            token_preview = token[:10] + "..." + token[-10:]
            print(f"Token preview: {token_preview}")
            
            # Test the token with a simple Graph API call
            print("\nTesting token with Graph API call to /me...")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            response = requests.get(
                f"{GRAPH_BASE_URL}/me",
                headers=headers
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Token works! User: {user_data.get('displayName')} ({user_data.get('userPrincipalName')})")
            else:
                print(f"❌ Token doesn't work. Status code: {response.status_code}")
                print(f"Response: {response.text}")
            
            # Save cache
            if cache.has_state_changed:
                with open(token_cache_path, "w") as file:
                    file.write(cache.serialize())
                print(f"Token cache saved to: {token_cache_path}")
            
            return True
        else:
            error_description = result.get("error_description", "Unknown error")
            error = result.get("error", "Unknown error")
            print(f"❌ Authentication failed: {error} - {error_description}")
            return False
    
    except Exception as e:
        print(f"❌ Error during authentication test: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def test_root_files():
    """Test getting root files from OneDrive."""
    try:
        print("\n=== Testing Root Files Access ===\n")
        
        # Get token
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as file:
                cache.deserialize(file.read())
        
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        accounts = app.get_accounts()
        if not accounts:
            print("❌ No accounts found in cache. Please run authentication test first.")
            return False
        
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result:
            print("❌ Failed to acquire token silently. Please run authentication test first.")
            return False
        
        token = result['access_token']
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get items in the root folder
        print("Getting items in the root folder...")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/root/children",
            headers=headers
        )
        
        if response.status_code == 200:
            # Parse response
            items = response.json().get('value', [])
            
            # Filter for files only (not folders)
            files = [item for item in items if 'file' in item]
            folders = [item for item in items if 'folder' in item]
            
            print(f"✅ Successfully retrieved root items: {len(files)} files and {len(folders)} folders")
            
            # Print list of files
            if files:
                print("\nFiles in the root:")
                for i, file in enumerate(files):
                    name = file.get('name', 'unknown')
                    size = file.get('size', 0)
                    size_mb = size / (1024 * 1024)
                    print(f"  {i+1}. {name} ({size_mb:.2f} MB)")
            else:
                print("\nNo files found in the root.")
            
            return True
        else:
            print(f"❌ Failed to get root items. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error testing root files access: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def test_download_capability():
    """Test downloading a small file from OneDrive."""
    try:
        print("\n=== Testing Download Capability ===\n")
        
        # Get token
        cache = msal.SerializableTokenCache()
        token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")
        if os.path.exists(token_cache_path):
            with open(token_cache_path, "r") as file:
                cache.deserialize(file.read())
        
        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            token_cache=cache
        )
        
        accounts = app.get_accounts()
        if not accounts:
            print("❌ No accounts found in cache. Please run authentication test first.")
            return False
        
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if not result:
            print("❌ Failed to acquire token silently. Please run authentication test first.")
            return False
        
        token = result['access_token']
        
        # Set up headers
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get items in the root folder
        print("Getting items in the root folder...")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/root/children",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get root items. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse response
        items = response.json().get('value', [])
        
        # Filter for files only (not folders)
        files = [item for item in items if 'file' in item]
        
        if not files:
            print("❌ No files found in the root to test download.")
            return False
        
        # Find the smallest file to test download
        smallest_file = min(files, key=lambda x: x.get('size', float('inf')))
        name = smallest_file.get('name', 'unknown')
        size = smallest_file.get('size', 0)
        size_mb = size / (1024 * 1024)
        file_id = smallest_file.get('id')
        
        print(f"Selected file for download test: {name} ({size_mb:.2f} MB)")
        
        # Get download URL
        print(f"Getting download URL...")
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/items/{file_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get download URL. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        download_url = response.json().get('@microsoft.graph.downloadUrl')
        if not download_url:
            print(f"❌ Could not get download URL for file: {name}")
            return False
        
        # Create test download directory
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_download")
        os.makedirs(test_dir, exist_ok=True)
        
        # Download the file
        print(f"Downloading file...")
        response = requests.get(download_url, stream=True)
        
        if response.status_code != 200:
            print(f"❌ Failed to download file. Status code: {response.status_code}")
            return False
        
        # Save the file
        file_path = os.path.join(test_dir, name)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify the file was downloaded
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ Successfully downloaded file: {file_path}")
            print(f"File size: {file_size} bytes")
            
            # Clean up
            os.remove(file_path)
            print(f"Test file removed.")
            
            return True
        else:
            print(f"❌ Failed to save downloaded file.")
            return False
    
    except Exception as e:
        print(f"❌ Error testing download capability: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def main():
    """Main function."""
    print("\n=== OneDrive API Test Tool ===\n")
    
    print("This tool will test various aspects of the OneDrive API to help diagnose issues.")
    print("Options:")
    print("1. Test Authentication")
    print("2. Test Root Files Access")
    print("3. Test Download Capability")
    print("4. Clear Token Cache")
    print("5. Run All Tests")
    print("6. Exit")
    
    choice = input("\nEnter your choice (1-6): ")
    
    if choice == "1":
        test_authentication()
    elif choice == "2":
        test_root_files()
    elif choice == "3":
        test_download_capability()
    elif choice == "4":
        clear_token_cache()
    elif choice == "5":
        auth_success = test_authentication()
        if auth_success:
            root_success = test_root_files()
            if root_success:
                download_success = test_download_capability()
                if download_success:
                    print("\n✅ All tests passed successfully!")
                else:
                    print("\n❌ Download test failed.")
            else:
                print("\n❌ Root files test failed.")
        else:
            print("\n❌ Authentication test failed.")
    else:
        print("\nExiting.")

if __name__ == "__main__":
    main()
