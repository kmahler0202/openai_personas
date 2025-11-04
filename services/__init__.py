"""
Services package for Google API integrations.

Provides reusable services for Gmail, Google Drive, and Google Docs.
"""

from .google_auth import get_google_services
from .gmail_service import send_email, send_google_doc_email, send_deck_with_attachment, send_rfp_answers_email
from .gdrive_service import upload_markdown_to_doc, share_document, upload_file_to_drive

__all__ = [
    'get_google_services',
    'send_email',
    'send_google_doc_email',
    'send_deck_with_attachment',
    'send_rfp_answers_email',
    'upload_markdown_to_doc',
    'share_document',
    'upload_file_to_drive'
]
