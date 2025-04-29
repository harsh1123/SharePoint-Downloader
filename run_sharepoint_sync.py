"""
Script to run the Organizational SharePoint Sync Tool.
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join('Sharepointsub', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")
    print("Please create a .env file with your SharePoint credentials.")
    print("You can use the .env.template file as a starting point.")

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Sharepointsub.main import main

if __name__ == "__main__":
    # Pass any command line arguments to the main function
    sys.exit(main())
