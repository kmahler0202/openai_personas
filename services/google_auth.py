"""
Google API Authentication Service

Handles OAuth2 authentication for Google Docs, Drive, and Gmail APIs.
"""

import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes required for all Google API operations
SCOPES = [
    "https://www.googleapis.com/auth/drive",  # Full Drive access (read/write)
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.send",
]

# Get the auth folder path (services/auth/)
AUTH_DIR = Path(__file__).parent / "auth"
TOKEN_PATH = AUTH_DIR / "token.json"
CLIENT_SECRET = AUTH_DIR / "credentials.json"


def get_google_services():
    """
    Authenticate and return Google API service clients.
    
    Returns:
        tuple: (docs_service, drive_service, gmail_service)
            - docs_service: Google Docs API client
            - drive_service: Google Drive API client
            - gmail_service: Gmail API client
    
    Raises:
        FileNotFoundError: If credentials.json is missing
    """
    creds = None
    
    # Ensure auth directory exists
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing credentials if available
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                raise FileNotFoundError(
                    f"Missing '{CLIENT_SECRET}'. Download from Google Cloud Console "
                    f"and place in {AUTH_DIR}/"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    
    # Build and return all service clients
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    gmail_service = build("gmail", "v1", credentials=creds)
    
    return docs_service, drive_service, gmail_service
