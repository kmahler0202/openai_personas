"""
Google Drive Service

Provides Google Drive and Google Docs operations including:
- Uploading Markdown to Google Docs
- Sharing documents
- Document permissions management
"""

import io
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import PyPDF2
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


def upload_markdown_to_doc(
    drive_service,
    md_content: str,
    title: str
) -> Dict[str, Any]:
    """
    Upload Markdown content as a Google Doc.
    
    Args:
        drive_service: Authenticated Google Drive API service client
        md_content: Markdown content as a string
        title: Title for the Google Doc
    
    Returns:
        dict: Created document metadata including:
            - id: Document ID
            - name: Document name
            - webViewLink: URL to view the document
    
    Raises:
        Exception: If upload fails
    """
    # Create temporary markdown file
    with tempfile.NamedTemporaryFile(
        mode='w',
        delete=False,
        suffix='.md',
        encoding='utf-8'
    ) as tf:
        tf.write(md_content)
        temp_path = tf.name
    
    try:
        file_metadata = {
            "name": title,
            "mimeType": "application/vnd.google-apps.document",
        }
        
        media = MediaFileUpload(
            temp_path,
            mimetype="text/markdown",
            resumable=False
        )
        
        created = (
            drive_service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,name,webViewLink"
            )
            .execute()
        )
        
        print(f"✅ Google Doc created: {created.get('name')}")
        return created
        
    finally:
        # Clean up temporary file
        import os
        try:
            os.remove(temp_path)
        except OSError:
            pass


def share_document(
    drive_service,
    file_id: str,
    recipient_email: str,
    role: str = "owner"
) -> None:
    """
    Share a Google Drive document with a specific user.
    
    Args:
        drive_service: Authenticated Google Drive API service client
        file_id: Google Drive file ID
        recipient_email: Email address to share with
        role: Permission role - "reader", "writer", or "owner" (default: "owner")
    
    Raises:
        Exception: If sharing fails
    """
    try:
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": recipient_email,
        }
        
        drive_service.permissions().create(
            fileId=file_id,
            body=permission,
            transferOwnership=True,
        ).execute()
        
        print(f"✅ Shared document with {recipient_email} ({role})")
        
    except Exception as e:
        print(f"⚠️ Could not share document: {e}")
        raise


def upload_file_to_drive(
    drive_service,
    file_path: str,
    title: Optional[str] = None,
    mime_type: Optional[str] = None,
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload any file to Google Drive.
    
    Args:
        drive_service: Authenticated Google Drive API service client
        file_path: Path to the file to upload
        title: Optional title for the file (defaults to filename)
        mime_type: Optional MIME type (auto-detected if not provided)
        folder_id: Optional Google Drive folder ID to upload to
    
    Returns:
        dict: Uploaded file metadata including:
            - id: File ID
            - name: File name
            - webViewLink: URL to view the file
            - webContentLink: URL to download the file
    
    Raises:
        Exception: If upload fails
    """
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_metadata = {
        "name": title or file_path_obj.name,
    }
    
    if folder_id:
        file_metadata["parents"] = [folder_id]
    
    media = MediaFileUpload(
        str(file_path),
        mimetype=mime_type,
        resumable=True
    )
    
    uploaded = (
        drive_service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink,webContentLink"
        )
        .execute()
    )
    
    print(f"✅ File uploaded to Drive: {uploaded.get('name')}")
    return uploaded


def extract_pdf_text_from_drive(
    drive_service,
    file_id: str
) -> str:
    """
    Download a PDF from Google Drive and extract its text content.
    
    Args:
        drive_service: Authenticated Google Drive API service client
        file_id: Google Drive file ID of the PDF
    
    Returns:
        str: Extracted text content from the PDF
    
    Raises:
        Exception: If download or text extraction fails
    """
    try:
        # Download the PDF file from Drive
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")
        
        print("✅ PDF downloaded from Drive")
        
        # Extract text from the PDF
        fh.seek(0)  # Reset file pointer to beginning
        pdf_reader = PyPDF2.PdfReader(fh)
        
        text = ""
        total_pages = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            text += f"\n--- Page {page_num + 1} of {total_pages} ---\n{page_text}"
        
        print(f"✅ Extracted text from {total_pages} pages")
        return text
        
    except Exception as e:
        print(f"❌ Error extracting PDF text from Drive: {e}")
        raise
