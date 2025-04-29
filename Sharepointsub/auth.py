"""
Authentication module for Microsoft Graph API using client credentials flow.
"""
import msal
import logging
from .config import TENANT_ID, CLIENT_ID, CLIENT_SECRET

class SharePointAuth:
    """
    Handles authentication with Microsoft Graph API using client credentials flow.
    This is suitable for organizational scenarios where you have registered an application
    with client ID and secret.
    """
    def __init__(self):
        """Initialize the authentication handler."""
        self.tenant_id = TENANT_ID
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.access_token = None
        
    def get_token(self):
        """
        Get an access token for Microsoft Graph API using client credentials flow.
        This method is suitable for service applications running without user interaction.
        """
        try:
            # Create the MSAL confidential client application
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            
            # Acquire token for client
            result = app.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                self.access_token = result['access_token']
                logging.info("Successfully acquired access token")
                return self.access_token
            else:
                error_description = result.get("error_description", "Unknown error")
                error = result.get("error", "Unknown error")
                logging.error(f"Authentication failed: {error} - {error_description}")
                raise Exception(f"Authentication failed: {error} - {error_description}")
        
        except Exception as e:
            logging.error(f"Error during authentication: {str(e)}")
            raise
    
    def get_headers(self):
        """Get the authorization headers for API requests."""
        if not self.access_token:
            self.get_token()
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
