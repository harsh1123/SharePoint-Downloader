# OneDrive Sync Tool for Individual Users

A Python application that connects to Microsoft OneDrive via Microsoft Graph API and downloads files locally, implementing delta sync for efficient synchronization.

## Features

- Works with personal Microsoft accounts (Outlook.com, Hotmail.com, etc.)
- Interactive authentication with token caching
- Delta sync to efficiently download only changed files
- Continuous or one-time sync options
- Detailed logging
- Configurable exclusion rules for file types and paths
- Preserves folder structure

## Prerequisites

- Python 3.6 or higher
- A personal Microsoft account with access to OneDrive
- Internet connection for authentication and downloading files

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Tool

```bash
python run.py
```

The first time you run the tool, it will:
1. Open a browser window for you to sign in with your Microsoft account
2. Download all files from your OneDrive to the `downloads` folder
3. Save the sync state for future runs

For subsequent runs, it will only download files that have changed since the last sync.

## Usage

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

## Configuration

You can modify the following settings in the `config.py` file:

- `DOWNLOAD_PATH`: The local directory where files will be downloaded
- `SYNC_INTERVAL_MINUTES`: How often to sync in continuous mode
- `FILE_TYPES_TO_EXCLUDE`: File extensions to exclude from sync
- `PATHS_TO_EXCLUDE`: Paths to exclude from sync

## How It Works

This application uses:
- Microsoft Authentication Library (MSAL) for secure authentication
- Microsoft Graph API to access OneDrive files
- Delta query feature for efficient synchronization
- Interactive authentication flow that works with personal accounts

## Troubleshooting

- Check the log file at `sync.log` for detailed information
- If authentication fails, try deleting the `.token_cache` file and running again
- For connection issues, check your internet connection and try again

## Security Notes

- The application uses secure token-based authentication
- Your Microsoft credentials are never stored by the application
- Authentication tokens are cached locally for convenience
- You can clear the token cache by deleting the `.token_cache` file
