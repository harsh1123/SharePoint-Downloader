"""
Troubleshooting script for SharePoint authentication issues.
This script tests different authentication approaches and provides detailed diagnostics.
"""
import os
import sys
import json
import logging
import requests
import msal
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auth_troubleshoot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logging.info(f"Loaded environment variables from {env_path}")
else:
    logging.error(f"No .env file found at {env_path}")
    sys.exit(1)

# Get credentials from environment variables
tenant_id = os.environ.get("SHAREPOINT_TENANT_ID")
client_id = os.environ.get("SHAREPOINT_CLIENT_ID")
client_secret = os.environ.get("SHAREPOINT_CLIENT_SECRET")
client_secret_id = os.environ.get("SHAREPOINT_CLIENT_SECRET_ID")
site_url = os.environ.get("SHAREPOINT_SITE_URL")

# Validate credentials
missing_vars = []
if not tenant_id or tenant_id == "your_tenant_id":
    missing_vars.append("SHAREPOINT_TENANT_ID")
if not client_id or client_id == "your_client_id":
    missing_vars.append("SHAREPOINT_CLIENT_ID")
if not client_secret or client_secret == "your_client_secret":
    missing_vars.append("SHAREPOINT_CLIENT_SECRET")
if not client_secret_id or client_secret_id == "your_client_secret_id":
    missing_vars.append("SHAREPOINT_CLIENT_SECRET_ID")
if not site_url or site_url == "your_sharepoint_site_url":
    missing_vars.append("SHAREPOINT_SITE_URL")

if missing_vars:
    logging.error(f"Missing or invalid environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

logging.info("All required environment variables are present")
logging.info(f"Tenant ID: {tenant_id}")
logging.info(f"Client ID: {client_id}")
logging.info(f"Site URL: {site_url}")
logging.info(f"Client Secret (first 4 chars): {client_secret[:4]}...")
logging.info(f"Client Secret ID (first 4 chars): {client_secret_id[:4]}...")

# Test different authentication approaches
def test_auth_approach(approach_name, authority, scopes, credential):
    """Test a specific authentication approach and return the result."""
    logging.info(f"\nTesting authentication approach: {approach_name}")
    logging.info(f"Authority: {authority}")
    logging.info(f"Scopes: {scopes}")
    
    try:
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=credential
        )
        
        logging.info("MSAL application created successfully")
        logging.info("Acquiring token...")
        
        result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            token = result["access_token"]
            token_preview = token[:10] + "..." + token[-10:]
            logging.info(f"Successfully acquired token: {token_preview}")
            
            # Test the token with a simple Graph API call
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            logging.info("Testing token with Graph API call to /me...")
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            
            logging.info(f"Response status code: {response.status_code}")
            if response.status_code == 200:
                logging.info("Token works for /me endpoint")
            else:
                logging.info(f"Token doesn't work for /me endpoint: {response.text}")
            
            # Test with SharePoint site
            logging.info(f"Testing token with SharePoint site: {site_url}")
            site_parts = site_url.split('/')
            hostname = site_parts[2]  # e.g., contoso.sharepoint.com
            
            if '/sites/' in site_url:
                site_name = site_url.split('/sites/')[1].split('/')[0]
                graph_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site_name}"
            else:
                graph_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}"
            
            logging.info(f"Making request to: {graph_url}")
            response = requests.get(
                graph_url,
                headers=headers
            )
            
            logging.info(f"Response status code: {response.status_code}")
            if response.status_code == 200:
                logging.info("Token works for SharePoint site!")
                site_data = response.json()
                logging.info(f"Site name: {site_data.get('displayName')}")
                logging.info(f"Site ID: {site_data.get('id')}")
                return True, token
            else:
                logging.info(f"Token doesn't work for SharePoint site: {response.text}")
            
            return True, token
        else:
            error = result.get("error", "unknown")
            error_description = result.get("error_description", "No description")
            logging.error(f"Failed to acquire token: {error} - {error_description}")
            return False, None
    
    except Exception as e:
        logging.error(f"Exception during authentication: {str(e)}")
        return False, None

# Test different approaches
approaches = [
    {
        "name": "Standard approach with client secret",
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "scopes": ["https://graph.microsoft.com/.default"],
        "credential": client_secret
    },
    {
        "name": "Using client secret ID as credential",
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "scopes": ["https://graph.microsoft.com/.default"],
        "credential": client_secret_id
    },
    {
        "name": "Using dictionary with secret key",
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "scopes": ["https://graph.microsoft.com/.default"],
        "credential": {"secret": client_secret}
    },
    {
        "name": "Using dictionary with both secret and secret ID",
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "scopes": ["https://graph.microsoft.com/.default"],
        "credential": {"secret": client_secret, "secret_id": client_secret_id}
    },
    {
        "name": "Using common authority",
        "authority": "https://login.microsoftonline.com/common",
        "scopes": ["https://graph.microsoft.com/.default"],
        "credential": client_secret
    },
    {
        "name": "Using organizations authority",
        "authority": "https://login.microsoftonline.com/organizations",
        "scopes": ["https://graph.microsoft.com/.default"],
        "credential": client_secret
    },
    {
        "name": "Using specific scopes",
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "scopes": ["https://graph.microsoft.com/Sites.Read.All", "https://graph.microsoft.com/Files.Read.All"],
        "credential": client_secret
    }
]

# Try each approach
success = False
working_token = None

for approach in approaches:
    result, token = test_auth_approach(
        approach["name"],
        approach["authority"],
        approach["scopes"],
        approach["credential"]
    )
    
    if result:
        success = True
        working_token = token
        logging.info(f"\n✅ SUCCESS with approach: {approach['name']}")
        break
    else:
        logging.info(f"\n❌ FAILED with approach: {approach['name']}")

if success:
    logging.info("\n=== AUTHENTICATION SUCCESSFUL ===")
    logging.info("Found a working authentication approach!")
    
    # Test SharePoint site access with the working token
    headers = {
        "Authorization": f"Bearer {working_token}",
        "Accept": "application/json"
    }
    
    # Try to get drives from the site
    logging.info("\nTesting access to SharePoint drives...")
    
    # Parse the site URL to extract the host and path
    site_parts = site_url.split('/')
    hostname = site_parts[2]  # e.g., contoso.sharepoint.com
    
    if '/sites/' in site_url:
        site_name = site_url.split('/sites/')[1].split('/')[0]
        site_endpoint = f"sites/{hostname}:/sites/{site_name}"
    else:
        site_endpoint = f"sites/{hostname}"
    
    # Get the site
    logging.info(f"Getting site information from: {site_endpoint}")
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/{site_endpoint}",
        headers=headers
    )
    
    if response.status_code == 200:
        site_data = response.json()
        site_id = site_data.get('id')
        logging.info(f"Successfully retrieved site. ID: {site_id}")
        
        # Get drives
        logging.info(f"Getting drives for site ID: {site_id}")
        response = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives",
            headers=headers
        )
        
        if response.status_code == 200:
            drives_data = response.json()
            drives = drives_data.get('value', [])
            logging.info(f"Successfully retrieved {len(drives)} drives")
            
            for i, drive in enumerate(drives):
                logging.info(f"Drive {i+1}: {drive.get('name')} (ID: {drive.get('id')})")
        else:
            logging.error(f"Failed to get drives: {response.status_code} - {response.text}")
    else:
        logging.error(f"Failed to get site: {response.status_code} - {response.text}")
else:
    logging.error("\n=== ALL AUTHENTICATION APPROACHES FAILED ===")
    logging.error("Please check your credentials and permissions")
    logging.error("Make sure your application has the necessary API permissions in Azure AD")
    logging.error("Ensure admin consent has been granted for the required permissions")

logging.info("\nTroubleshooting complete. Check auth_troubleshoot.log for details.")
