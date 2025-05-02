# OneDrive Sync Tool for Individual Users

A Python application that connects to Microsoft OneDrive via Microsoft Graph API and downloads files locally, implementing manual state tracking for efficient synchronization.

## Features

- Works with personal Microsoft accounts (Outlook.com, Hotmail.com, etc.)
- Interactive authentication with token caching
- Manual state tracking to efficiently download only changed files
- Multiple sync modes (full, test, root-only, folder-specific)
- Continuous or one-time sync options
- Comprehensive logging and troubleshooting
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

### Basic Sync Options

#### One-time Sync

Run the script to perform a one-time synchronization:

```bash
python run.py
```

#### Continuous Sync

Run the script in continuous mode to keep syncing at regular intervals:

```bash
python run.py --continuous
```

### Selective Sync Options

#### Root-Only Mode

Download only files that are directly in the root of your OneDrive (not in any folder):

```bash
python run.py --root-only
```

#### Folder-Specific Sync

Download only files from a specific folder and its subfolders:

```bash
python run.py --folder "Documents"
```

#### Test Mode

Download only a limited number of files (default is 10):

```bash
python run.py --test
```

Specify the maximum number of files to download:

```bash
python run.py --test --max-files 5
```

#### Check-Only Mode

Check what would be downloaded without actually downloading:

```bash
python run.py --check-only
```

### Additional Options

#### Force Full Sync

Force a full sync by ignoring the existing state file:

```bash
python run.py --force-full-sync
```

#### Force Save State

Force saving the state file after sync:

```bash
python run.py --force-save-state
```

### Combining Options

You can combine multiple options for more specific syncing:

```bash
# Download up to 5 files from the root only
python run.py --root-only --test --max-files 5

# Check what root files would be downloaded without downloading
python run.py --root-only --check-only

# Continuously sync only the Documents folder
python run.py --folder "Documents" --continuous

# Force a full sync of root files only
python run.py --root-only --force-full-sync
```

### Logging Options

#### Verbose Output

Show more detailed output:

```bash
python run.py --verbose
```

#### Debug Mode

Show debug information:

```bash
python run.py --debug
```

### Troubleshooting Options

Run the troubleshooting script to diagnose issues:

```bash
python troubleshoot.py
```

Show the current sync state:

```bash
python run.py --show-state
```

Force a full sync (ignore existing delta link):

```bash
python run.py --force-full-sync
```

Force saving the state file after sync:

```bash
python run.py --force-save-state
```

Create a test state file (for debugging):

```bash
python run.py --create-test-state
```

## Configuration

### Config File Settings

You can modify the following settings in the `config.py` file:

- `DOWNLOAD_PATH`: The local directory where files will be downloaded
- `SYNC_INTERVAL_MINUTES`: How often to sync in continuous mode (default: 60 minutes)
- `FILE_TYPES_TO_EXCLUDE`: File extensions to exclude from sync (e.g., ['.tmp', '.bak'])
- `PATHS_TO_EXCLUDE`: Paths to exclude from sync (e.g., ['Documents/Archive'])
- `LOG_LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Log Files

The tool generates several log files:

- `sync.log`: Regular information about the sync process
- `debug.log`: Detailed debugging information
- `troubleshoot.log`: Results from the troubleshooting script

### State Files

- `.token_cache`: Stores authentication tokens (delete to force re-authentication)
- `onedrive_sync_state.json`: Stores file metadata and last sync time (located in your user home directory)

## How It Works

### Authentication

- Uses Microsoft Authentication Library (MSAL) for secure authentication
- Implements interactive authentication flow that works with personal accounts
- Caches authentication tokens locally for convenience
- Automatically refreshes tokens when they expire

### Synchronization

- Uses Microsoft Graph API to access OneDrive files
- Implements manual state tracking to efficiently track changes
- Only downloads new or modified files
- Preserves folder structure locally
- Supports selective syncing (root-only, folder-specific, etc.)

### Manual State Tracking

Manual state tracking is a key feature that makes this tool efficient:
1. On first run, it downloads all files (based on your selected options)
2. It saves metadata about each file (ID, name, path, modification time, size)
3. On subsequent runs, it compares the current state with the saved state
4. It only downloads files that are new or have changed
5. This significantly reduces bandwidth usage and sync time

## Troubleshooting

### Common Issues

- **Authentication Fails**: Delete the `.token_cache` file and run again
- **Files Not Downloading**: Check the sync.log file for error messages
- **Sync Seems Slow**: The first sync downloads all files and can take time
- **Permission Errors**: Make sure you grant all requested permissions during authentication
- **State File Issues**: Use `delete_state.py` to remove the state file and force a full sync
- **No Changes Detected**: Use `--force-full-sync` to ignore the existing state file

### Using the Troubleshooting Script

For comprehensive diagnostics, run:

```bash
python troubleshoot.py
```

This script will:
1. Check your system configuration
2. Test authentication with Microsoft
3. Verify access to your OneDrive
4. Test delta sync functionality
5. Generate a detailed troubleshooting report

### Logs

Check these logs if you encounter any issues:
- `sync.log`: Regular information about the sync process
- `debug.log`: Detailed debugging information
- `troubleshoot.log`: Results from the troubleshooting script

## Security Notes

- The application uses secure token-based authentication
- Your Microsoft credentials are never stored by the application
- Authentication tokens are cached locally for convenience
- You can clear the token cache by deleting the `.token_cache` file
- The application only requests read access to your OneDrive files
