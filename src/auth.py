"""
Authentication module for Microsoft Graph API using MSAL.
"""
import msal
import os
from .config import CLIENT_ID, AUTHORITY, SCOPE, TOKEN_CACHE_FILE

class GraphAuth:
    """
    Handles authentication with Microsoft Graph API using MSAL.
    """
    def __init__(self):
        """Initialize the authentication handler."""
        self.client_id = CLIENT_ID
        self.authority = AUTHORITY
        self.scope = SCOPE
        self.token_cache_file = TOKEN_CACHE_FILE
        self.app = self._create_app()
        self.access_token = None

    def _create_app(self):
        """Create the MSAL application with token cache."""
        cache = msal.SerializableTokenCache()

        # Load token cache from file if it exists
        if os.path.exists(self.token_cache_file):
            with open(self.token_cache_file, 'r') as f:
                cache.deserialize(f.read())

        # Create the MSAL application
        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=cache
        )

        return app

    def _save_cache(self):
        """Save the token cache to file."""
        if self.app.token_cache.has_state_changed:
            with open(self.token_cache_file, 'w') as f:
                f.write(self.app.token_cache.serialize())

    def get_token(self):
        """
        Get an access token for Microsoft Graph API.
        First tries to get a token from the cache, then falls back to interactive login.
        """
        # Try to get token from cache first
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(self.scope, account=accounts[0])
            if result:
                self.access_token = result['access_token']
                return self.access_token

        # If no token in cache or expired, try interactive login
        print("\nYou will be redirected to your browser to sign in with your Microsoft account.")
        print("If no browser opens automatically, check for a minimized browser window or manually go to the URL that will be displayed.")

        # Try interactive login with specific parameters for better compatibility
        result = self.app.acquire_token_interactive(
            scopes=self.scope,
            prompt="select_account",  # Forces account selection to avoid cached credentials issues
            login_hint="",  # Clear any previous login hints
        )

        if "access_token" in result:
            self.access_token = result['access_token']
            self._save_cache()
            return self.access_token
        else:
            error_description = result.get("error_description", "Unknown error")
            error = result.get("error", "Unknown error")
            raise Exception(f"Authentication failed: {error} - {error_description}")

    def get_headers(self):
        """Get the authorization headers for API requests."""
        if not self.access_token:
            self.get_token()

        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
