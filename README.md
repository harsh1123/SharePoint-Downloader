# SharePoint File Downloader

A Python application that connects to Microsoft SharePoint/OneDrive for Business via Microsoft Graph API and downloads files locally.

## Features

- Secure authentication using Microsoft Authentication Library (MSAL)
- List available drives and files from SharePoint/OneDrive for Business
- Download files and folders while preserving folder structure
- Simple command-line interface
- Works for individual Microsoft 365 users without admin rights
- Option to download all files automatically

## Prerequisites

- Python 3.6 or higher
- A Microsoft 365 account with access to SharePoint/OneDrive for Business
- Internet connection for authentication and downloading files
- Your own Microsoft Azure application registration (see Setup section)

## Setup

### 1. Register an Application in Azure Portal

1. Go to the [Azure Portal App Registration page](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Sign in with your Microsoft account
3. Click on "New registration"
4. Fill in the registration form:
   - Name: "SharePoint File Downloader" (or any name you prefer)
   - Supported account types: Select "Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)"
   - Redirect URI: Select "Public client/native (mobile & desktop)" and enter "http://localhost"
5. Click "Register"
6. After registration, note down the "Application (client) ID" - you'll need this value

### 2. Configure API Permissions

1. In your app's page, click on "API permissions" in the left sidebar
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions"
5. Search for and select the following permissions:
   - Files.Read
   - Files.Read.All
   - Sites.Read.All
6. Click "Add permissions"

### 3. Configure the Application

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your client ID:

```
GRAPH_CLIENT_ID=your_client_id_here
```

## Usage

### Interactive Mode

Run the main script to browse and download files interactively:

```bash
python main.py
```

The application will:
1. Open a browser window for you to authenticate with your Microsoft 365 account
2. List available drives (OneDrive/SharePoint sites)
3. Allow you to select which drive to browse
4. Let you navigate folders and download files

### Download All Files Automatically

To download all files from your OneDrive/SharePoint automatically:

```bash
python download_all.py
```

This will:
1. Authenticate with your Microsoft 365 account
2. Find all available drives
3. Download all files and folders, preserving the folder structure
4. Save everything to the "downloads" folder

## Configuration

You can modify the following settings in the `config.py` file:
- `DOWNLOAD_PATH`: The local directory where files will be downloaded
- `TOKEN_CACHE_FILE`: Location to store the authentication token cache

## How It Works

This application uses:
- Microsoft Authentication Library (MSAL) for secure authentication
- Microsoft Graph API to access SharePoint and OneDrive for Business files
- Interactive authentication flow that works with MFA-enabled accounts

## Security Notes

- The application uses secure token-based authentication
- Your Microsoft 365 credentials are never stored by the application
- Authentication tokens are cached locally for convenience
- You can clear the token cache by deleting the `.token_cache` file
- Your client ID is stored in the `.env` file which is not committed to version control

## Troubleshooting

- If authentication fails, ensure you have the correct permissions to access SharePoint
- For connection issues, check your internet connection and try again
- If you encounter "Access Denied" errors, ensure your account has access to the requested resources

## License

This project is licensed under the MIT License - see the LICENSE file for details.
