"""
Authentication module for Microsoft Graph API using interactive authentication.
This is suitable for individual users with personal Microsoft accounts.
"""
import msal
import logging
import webbrowser
import time
import os
from config import CLIENT_ID, AUTHORITY, SCOPES

class OneDriveAuth:
    """
    Handles authentication with Microsoft Graph API using interactive authentication.
    This is suitable for individual users with personal Microsoft accounts.
    """
    def __init__(self):
        """Initialize the authentication handler."""
        self.client_id = CLIENT_ID
        self.authority = AUTHORITY
        self.scopes = SCOPES
        self.access_token = None
        self.token_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache")

    def _load_cache(self):
        """Load token cache from file if it exists."""
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_file):
            with open(self.token_cache_file, "r") as file:
                cache.deserialize(file.read())
        return cache

    def _save_cache(self, cache):
        """Save token cache to file."""
        if cache.has_state_changed:
            with open(self.token_cache_file, "w") as file:
                file.write(cache.serialize())

    def get_token(self):
        """
        Get an access token for Microsoft Graph API.
        First tries to get a token from the cache, then falls back to interactive login.
        """
        try:
            # Load token cache
            cache = self._load_cache()

            # Create the MSAL public client application
            app = msal.PublicClientApplication(
                self.client_id,
                authority=self.authority,
                token_cache=cache
            )

            # Try to get token from cache first
            accounts = app.get_accounts()
            if accounts:
                logging.info("Found account in cache, attempting to get token silently")
                result = app.acquire_token_silent(self.scopes, account=accounts[0])
                if result:
                    self.access_token = result['access_token']
                    logging.info("Successfully acquired token from cache")
                    self._save_cache(cache)
                    return self.access_token

            # If no token in cache or expired, try device code flow first
            logging.info("No valid token in cache, attempting device code flow")
            flow = app.initiate_device_flow(scopes=self.scopes)

            if "user_code" in flow:
                # Print the message with the code for the user
                print("\n" + flow["message"])
                print("\nWaiting for you to complete the authentication in your browser...")

                # Try to open the verification URL automatically
                try:
                    webbrowser.open(flow["verification_uri"])
                except:
                    pass

                # Complete the flow by waiting for the user to enter the code
                result = app.acquire_token_by_device_flow(flow)
            else:
                # If device code flow fails, fall back to interactive login
                logging.info("Device code flow failed, attempting interactive login")
                print("\nYou will be redirected to your browser to sign in with your Microsoft account.")
                result = app.acquire_token_interactive(self.scopes)

            if "access_token" in result:
                self.access_token = result['access_token']
                logging.info("Successfully acquired token through interactive login")
                self._save_cache(cache)
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
