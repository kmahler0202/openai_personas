#!/usr/bin/env python3
"""
Convert a Markdown file (text only) to a styled Google Doc using Google Drive’s
native Markdown import.  This version removes all Mermaid/Kroki logic.

Usage:
  python md_to_gdoc_text.py input.md --title "My Google Doc"
"""

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# --- Configuration ---
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
]
TOKEN_PATH = "token.json"
CLIENT_SECRET = "credentials.json"


# ---------------------------------------------------------------------
#  Google API Authentication
# ---------------------------------------------------------------------
def get_google_services():
    """Authenticate and return Docs and Drive service clients."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET):
                raise FileNotFoundError(
                    f"Missing '{CLIENT_SECRET}'. Download from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return docs_service, drive_service


# ---------------------------------------------------------------------
#  Core: upload Markdown → Google Doc
# ---------------------------------------------------------------------
def upload_markdown_as_doc(drive_service, md_path: Path, title: Optional[str]) -> Dict[str, Any]:
    """
    Upload a Markdown file to Google Drive and automatically convert it to a Google Doc.
    """
    file_metadata = {
        "name": title or md_path.stem,
        "mimeType": "application/vnd.google-apps.document",
    }
    media = MediaFileUpload(str(md_path), mimetype="text/markdown", resumable=False)
    created = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id,name,webViewLink")
        .execute()
    )
    return created


# ---------------------------------------------------------------------
#  Full Pipeline
# ---------------------------------------------------------------------
def full_pipeline(
    content: str | Path,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    End-to-end Markdown → Google Doc pipeline (text only).

    Steps:
      1. Accept raw Markdown string or a path.
      2. Write temp Markdown file if input is inline text.
      3. Authenticate with Google.
      4. Upload via Drive and convert to a Google Doc.
      5. Return metadata: {'doc_id', 'webViewLink', 'source'}
    """
    # Normalize input
    if isinstance(content, Path) or os.path.exists(str(content)):
        md_path = Path(str(content))
        raw_md = md_path.read_text(encoding="utf-8")
        source = str(md_path)
        default_title = md_path.stem
    else:
        raw_md = str(content)
        md_path = None
        source = "<inline>"
        default_title = "Imported Markdown"

    # Write temporary Markdown file if necessary
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as tf:
        tf.write(raw_md)
        tmp_md_path = Path(tf.name)

    try:
        # Auth + upload
        docs_service, drive_service = get_google_services()
        print("✨ Creating Google Doc from Markdown...")
        created = upload_markdown_as_doc(
            drive_service,
            tmp_md_path,
            title or default_title,
        )

        doc_id = created["id"]
        web_view = created.get("webViewLink") or f"https://docs.google.com/document/d/{doc_id}/edit"
        print(f"🎉 Google Doc created: {web_view}")

        return {
            "doc_id": doc_id,
            "webViewLink": web_view,
            "source_md": source,
        }

    finally:
        # Clean up temporary file
        try:
            os.remove(tmp_md_path)
        except OSError:
            pass


# ---------------------------------------------------------------------
#  CLI entrypoint
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Convert a Markdown file to a Google Doc via Drive import."
    )
    parser.add_argument("input", help="Path to the input .md file")
    parser.add_argument("--title", help="Optional title for the Google Doc", default=None)
    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    try:
        result = full_pipeline(md_path, args.title)
        print("\n✅ Done!")
        print(f"-> Open in browser: {result['webViewLink']}")
        print(f"📄 Document ID: {result['doc_id']}")
    except HttpError as err:
        print(f"\n❌ API error: {err}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
