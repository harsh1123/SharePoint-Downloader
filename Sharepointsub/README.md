# Organizational SharePoint Sync Tool

A Python application that connects to Microsoft SharePoint via Microsoft Graph API and downloads files locally, implementing manual state tracking for efficient synchronization.

## Features

- Secure authentication using client credentials flow (no user interaction required)
- Manual state tracking to efficiently download only changed files
- Continuous or one-time sync options
- Detailed logging
- Configurable exclusion rules for file types and paths
- Preserves folder structure

## Prerequisites

- Python 3.6 or higher
- A Microsoft 365 account with access to SharePoint
- Registered application in Azure AD with client ID and secret
- Proper permissions configured for the application

## Setup

### 1. Register an Application in Azure Portal

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to "Azure Active Directory" > "App registrations" > "New registration"
3. Fill in the registration form:
   - Name: "SharePoint Sync Tool" (or any name you prefer)
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Not required for this application
4. Click "Register"
5. Note down the "Application (client) ID" and "Directory (tenant) ID"

### 2. Create a Client Secret

1. In your app's page, click on "Certificates & secrets" in the left sidebar
2. Under "Client secrets", click "New client secret"
3. Add a description and select an expiration period
4. Click "Add"
5. Note down the secret value (you won't be able to see it again)

### 3. Configure API Permissions

1. In your app's page, click on "API permissions" in the left sidebar
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Application permissions"
5. Search for and select the following permissions:
   - Files.Read.All
   - Sites.Read.All
6. Click "Add permissions"
7. Click "Grant admin consent for [your organization]"

### 4. Configure the Application

1. Copy the `.env.template` file to `.env` in the Sharepointsub directory
2. Fill in your actual credentials:
   ```
   SHAREPOINT_TENANT_ID=your_tenant_id
   SHAREPOINT_CLIENT_ID=your_client_id
   SHAREPOINT_CLIENT_SECRET=your_client_secret
   SHAREPOINT_CLIENT_SECRET_ID=your_client_secret_id
   SHAREPOINT_SITE_URL=your_sharepoint_site_url
   ```

## Usage

### Using Batch Files

For convenience, several batch files are provided:

- `run_sharepoint_sync.bat` - Run a one-time sync
- `run_continuous_sync.bat` - Run in continuous mode
- `run_check_only.bat` - Check for changes without downloading
- `reset_and_run.bat` - Delete the state file and run a full sync

### Using Python Commands

### One-time Sync

Run the script to perform a one-time synchronization:

```bash
python run.py
```

### Continuous Sync

Run the script in continuous mode to keep syncing at regular intervals:

```bash
python run.py --continuous
```

### Check Only Mode

Check for changes without downloading files:

```bash
python run.py --check-only
```

### Reset State

Delete the state file to force a full sync on the next run:

```bash
python delete_state.py
```

## Configuration

You can modify the following settings in the `config.py` file:

- `DOWNLOAD_PATH`: The local directory where files will be downloaded
- `SYNC_INTERVAL_MINUTES`: How often to sync in continuous mode
- `FILE_TYPES_TO_EXCLUDE`: File extensions to exclude from sync
- `PATHS_TO_EXCLUDE`: Paths to exclude from sync

## How It Works

This application uses:
- Microsoft Authentication Library (MSAL) for secure authentication
- Microsoft Graph API to access SharePoint files
- Manual state tracking for efficient synchronization
- Client credentials flow for non-interactive authentication

### Manual State Tracking

Manual state tracking is a key feature that makes this tool efficient:
1. On first run, it downloads all files from your SharePoint site
2. It saves metadata about each file (ID, name, path, modification time, size)
3. On subsequent runs, it compares the current state with the saved state
4. It only downloads files that are new or have changed
5. This significantly reduces bandwidth usage and sync time

## Troubleshooting

- Check the log file at `Sharepointsub/sync.log` for detailed information
- Ensure your application has the correct permissions in Azure AD
- Verify that your SharePoint site URL is correct
- Make sure your client ID and secret are valid
- If sync is not working correctly, try using `reset_and_run.bat` to start fresh
- For authentication issues, check the `.env` file to ensure credentials are correct

## Security Notes

- The application uses secure token-based authentication
- Credentials are stored in the .env file (not committed to version control)
- The client secret should be treated as sensitive information
- Consider using a secrets manager for production deployments
