#!/usr/bin/env python3
"""
Convert a Markdown file (text only) to a styled Google Doc using Google Drive’s
native Markdown import. Now also supports automatic sharing and email delivery.
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

# >>> ADDED
from email.mime.text import MIMEText
import base64

# --- Configuration ---
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
    # >>> ADDED: Gmail send permission
    "https://www.googleapis.com/auth/gmail.send",
]
TOKEN_PATH = "token.json"
CLIENT_SECRET = "credentials.json"


# ---------------------------------------------------------------------
#  Google API Authentication
# ---------------------------------------------------------------------
def get_google_services():
    """Authenticate and return Docs, Drive, and Gmail service clients."""
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
    gmail_service = build("gmail", "v1", credentials=creds)  # >>> ADDED
    return docs_service, drive_service, gmail_service


# ---------------------------------------------------------------------
#  Upload Markdown → Google Doc
# ---------------------------------------------------------------------
def upload_markdown_as_doc(drive_service, md_path: Path, title: Optional[str]) -> Dict[str, Any]:
    """Upload a Markdown file to Google Drive and convert it to a Google Doc."""
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
#  >>> ADDED: Share Google Doc with recipient
# ---------------------------------------------------------------------
def share_document(drive_service, file_id: str, recipient_email: str, role="reader"):
    """Grants the specified email access to the document."""
    try:
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": recipient_email,
        }
        drive_service.permissions().create(
            fileId=file_id, body=permission, sendNotificationEmail=False
        ).execute()
        print(f"✅ Shared document with {recipient_email} ({role})")
    except Exception as e:
        print(f"⚠️ Could not share doc: {e}")


# ---------------------------------------------------------------------
#  >>> ADDED: Send Email via Gmail API
# ---------------------------------------------------------------------
def send_email_gmail_api(gmail_service, recipient_email: str, doc_link: str, doc_id: str, state: dict):
    """Sends a nicely formatted HTML email with the document link and metadata."""

    subject = "Your AI-Generated Report is Ready!"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>✅ Your AI Report is Complete</h2>

        <p>You can view it here:</p>
        <p><a href="{doc_link}" target="_blank">{doc_link}</a></p>
        <p><strong>Document ID:</strong> <code>{doc_id}</code></p>

        <hr>

        <h3>📊 Report Inputs</h3>
        <ul>
          <li><strong>Client:</strong> {state.get("client")}</li>
          <li><strong>Product Category:</strong> {state.get("product_category")}</li>
          <li><strong>Target Market Segments:</strong> {state.get("target_market_segments")}</li>
          <li><strong>Target Geographies:</strong> {state.get("target_geographies")}</li>
        </ul>

        <h3>⚙️ Generation Info</h3>
        <ul>
          <li><strong>Model Used:</strong> {state.get("model_used")}</li>
          <li><strong>Total Cost:</strong> ${state.get("total_cost"): .4f} USD</li>
          <li><strong>Runtime:</strong> {state.get("runtime_human")}</li>
        </ul>

        <hr>
        <small>Sent automatically by your AI Report Generator.</small>
      </body>
    </html>
    """

    message = MIMEText(body, "html")
    message["to"] = recipient_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print(f"📧 Email sent to {recipient_email} (Message ID: {sent['id']})")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


# ---------------------------------------------------------------------
#  Full Pipeline
# ---------------------------------------------------------------------
def full_pipeline(
    content: str | Path,
    title: Optional[str] = None,
    recipient_email: Optional[str] = None,  # >>> ADDED
    state: Optional[dict] = None,  # >>> ADDED
) -> Dict[str, Any]:
    """
    End-to-end Markdown → Google Doc pipeline (text only).

    Steps:
      3. Authenticate with Google.
      4. Upload via Drive and convert to a Google Doc.
      5. Optionally share with recipient + email them.
      6. Return metadata: {'doc_id', 'webViewLink', 'source'}
    """
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

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as tf:
        tf.write(raw_md)
        tmp_md_path = Path(tf.name)

    try:
        docs_service, drive_service, gmail_service = get_google_services()
        print("✨ Creating Google Doc from Markdown...")
        created = upload_markdown_as_doc(
            drive_service,
            tmp_md_path,
            title or default_title,
        )

        doc_id = created["id"]
        web_view = created.get("webViewLink") or f"https://docs.google.com/document/d/{doc_id}/edit"
        print(f"🎉 Google Doc created: {web_view}")

        # >>> ADDED: Share + Email Delivery
        if recipient_email:
            share_document(drive_service, doc_id, recipient_email, role="owner")
            send_email_gmail_api(gmail_service, recipient_email, web_view, doc_id, state)

        return {
            "doc_id": doc_id,
            "webViewLink": web_view,
            "source_md": source,
        }

    finally:
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
    parser.add_argument("--email", help="Email address to share + notify", default=None)  # >>> ADDED
    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    try:
        result = full_pipeline(md_path, args.title, recipient_email=args.email)
        print("\n✅ Done!")
        print(f"-> Open in browser: {result['webViewLink']}")
        print(f"📄 Document ID: {result['doc_id']}")
    except HttpError as err:
        print(f"\n❌ API error: {err}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
