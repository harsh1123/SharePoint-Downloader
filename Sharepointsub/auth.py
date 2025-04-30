"""
Authentication module for Microsoft Graph API using client credentials flow.
"""
import msal
import logging
from config import TENANT_ID, CLIENT_ID, CLIENT_SECRET, CLIENT_SECRET_ID

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
        self.client_secret_id = CLIENT_SECRET_ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.access_token = None

    def get_token(self):
        """
        Get an access token for Microsoft Graph API using client credentials flow.
        This method is suitable for service applications running without user interaction.
        """
        try:
            # Log the authentication parameters (without the secret)
            logging.debug(f"Authenticating with tenant ID: {self.tenant_id}")
            logging.debug(f"Client ID: {self.client_id}")
            logging.debug(f"Authority: {self.authority}")
            logging.debug(f"Scopes: {self.scope}")

            # Validate credentials
            if not self.tenant_id or self.tenant_id == "your_tenant_id":
                raise ValueError("Invalid tenant ID. Please check your .env file.")
            if not self.client_id or self.client_id == "your_client_id":
                raise ValueError("Invalid client ID. Please check your .env file.")
            if not self.client_secret or self.client_secret == "your_client_secret":
                raise ValueError("Invalid client secret. Please check your .env file.")
            if not self.client_secret_id or self.client_secret_id == "your_client_secret_id":
                raise ValueError("Invalid client secret ID. Please check your .env file.")

            # Create the MSAL confidential client application
            logging.debug("Creating MSAL application with client ID and credentials")

            # Try different credential formats based on what might be expected
            try:
                # First attempt: Use just the client secret (most common format)
                logging.debug("Attempting authentication with client secret only")
                app = msal.ConfidentialClientApplication(
                    self.client_id,
                    authority=self.authority,
                    client_credential=self.client_secret  # Just the secret as a string
                )
            except Exception as e:
                logging.debug(f"First authentication attempt failed: {str(e)}")

                try:
                    # Second attempt: Use the secret ID as the secret
                    logging.debug("Attempting authentication with client secret ID as the secret")
                    app = msal.ConfidentialClientApplication(
                        self.client_id,
                        authority=self.authority,
                        client_credential=self.client_secret_id  # Using the secret ID as the secret
                    )
                except Exception as e:
                    logging.debug(f"Second authentication attempt failed: {str(e)}")

                    try:
                        # Third attempt: Use a dictionary with the expected format
                        logging.debug("Attempting authentication with credential dictionary")
                        client_credential = {
                            "secret": self.client_secret,
                            "secret_id": self.client_secret_id
                        }
                        app = msal.ConfidentialClientApplication(
                            self.client_id,
                            authority=self.authority,
                            client_credential=client_credential
                        )
                    except Exception as e:
                        logging.debug(f"Third authentication attempt failed: {str(e)}")

                        # Final attempt: Try another dictionary format
                        logging.debug("Attempting authentication with alternative credential format")
                        client_credential = {
                            "clientSecret": self.client_secret,
                            "clientSecretId": self.client_secret_id
                        }
                        app = msal.ConfidentialClientApplication(
                            self.client_id,
                            authority=self.authority,
                            client_credential=client_credential
                        )

            # Acquire token for client
            logging.debug("Requesting access token...")
            result = app.acquire_token_for_client(scopes=self.scope)

            if "access_token" in result:
                self.access_token = result['access_token']
                logging.info("Successfully acquired access token")
                # Log a small portion of the token for debugging
                token_preview = self.access_token[:10] + "..." + self.access_token[-10:]
                logging.debug(f"Token preview: {token_preview}")
                return self.access_token
            else:
                error_description = result.get("error_description", "Unknown error")
                error = result.get("error", "Unknown error")
                logging.error(f"Authentication failed: {error} - {error_description}")

                # Provide more specific guidance based on error
                if "invalid_client" in error:
                    logging.error("This could be due to an incorrect client ID or secret. Please verify your credentials.")
                elif "invalid_grant" in error:
                    logging.error("This could be due to insufficient permissions. Check your app's API permissions in Azure Portal.")
                elif "unauthorized_client" in error:
                    logging.error("This app is not authorized to use this grant type. Make sure your app is configured correctly in Azure Portal.")

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
