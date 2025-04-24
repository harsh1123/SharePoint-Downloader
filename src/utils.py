"""
Utility functions for the SharePoint File Downloader.
"""
import os
import json
from datetime import datetime

def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def create_log_entry(action, status, details=None):
    """Create a log entry for actions."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status
    }
    
    if details:
        log_entry["details"] = details
    
    return log_entry

def save_log(log_entries, log_file):
    """Save log entries to a file."""
    with open(log_file, 'w') as f:
        json.dump(log_entries, f, indent=2)

def load_log(log_file):
    """Load log entries from a file."""
    if not os.path.exists(log_file):
        return []
    
    with open(log_file, 'r') as f:
        return json.load(f)

def validate_download(local_path, expected_size=None):
    """Validate that a file was downloaded correctly."""
    if not os.path.exists(local_path):
        return False
    
    if expected_size is not None:
        actual_size = os.path.getsize(local_path)
        return actual_size == expected_size
    
    return True
