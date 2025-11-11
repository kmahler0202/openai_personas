"""
ingest_pdfs.py
Script to ingest PDF documents into Pinecone vector database.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict
import PyPDF2
from openai import OpenAI
from dotenv import load_dotenv

from services.pinecone_db import upsert_vectors

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions
CHUNK_SIZE = 1500  # characters
CHUNK_OVERLAP = 300  # characters


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            text += f"\n--- Page {page_num + 1} ---\n{page_text}"
    
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        # Try to break at sentence or word boundary
        if end < len(text):
            last_period = chunk_text.rfind('.')
            last_newline = chunk_text.rfind('\n')
            last_space = chunk_text.rfind(' ')
            
            break_point = max(last_period, last_newline, last_space)
            if break_point > chunk_size * 0.8:
                end = start + break_point + 1
                chunk_text = text[start:end]
        
        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_text.strip(),
            "start_char": start,
            "end_char": end,
            "length": len(chunk_text.strip())
        })
        
        chunk_id += 1
        start = end - overlap
    
    return chunks


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts using OpenAI."""
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model=EMBEDDING_MODEL
        )
        embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(embeddings)
    
    return all_embeddings


def prepare_vectors(chunks: List[Dict], embeddings: List[List[float]], doc_id: str, pdf_path: str) -> List[Dict]:
    """Prepare vectors in Pinecone format."""
    vectors = []
    filename = os.path.basename(pdf_path)
    
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vector = {
            "id": f"{doc_id}_chunk_{idx}",
            "values": embedding,
            "metadata": {
                "text": chunk["text"][:1000],  # Limit metadata size
                "source": filename,
                "chunk_id": chunk["chunk_id"],
                "doc_id": doc_id,
                "length": chunk["length"],
                "page_info": "extracted"
            }
        }
        vectors.append(vector)
    
    return vectors


def ingest_pdf(pdf_path: str, doc_id: str = None) -> str:
    """
    Ingest a single PDF into Pinecone vector database.
    
    Args:
        pdf_path: Path to the PDF file
        doc_id: Optional unique identifier for the document
        
    Returns:
        Document ID used for ingestion
    """
    if not doc_id:
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        doc_id = f"{filename}_{timestamp}"
    
    print(f"\n{'='*60}")
    print(f"📄 INGESTING PDF")
    print(f"{'='*60}")
    print(f"File: {pdf_path}")
    print(f"Doc ID: {doc_id}\n")
    
    # Step 1: Extract text
    print("🔄 Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    print(f"✅ Extracted {len(text):,} characters")
    
    # Step 2: Chunk text
    print(f"🔄 Chunking text (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"✅ Created {len(chunks)} chunks")
    
    # Step 3: Generate embeddings
    print(f"🔄 Generating embeddings...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = generate_embeddings(texts)
    print(f"✅ Generated {len(embeddings)} embeddings")
    
    # Step 4: Prepare vectors
    print(f"🔄 Preparing vectors for Pinecone...")
    vectors = prepare_vectors(chunks, embeddings, doc_id, pdf_path)
    print(f"✅ Prepared {len(vectors)} vectors")
    
    # Step 5: Upload to Pinecone
    print(f"🔄 Uploading to Pinecone...")
    upsert_vectors(vectors)
    
    print(f"\n{'='*60}")
    print(f"✅ INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"Doc ID: {doc_id}")
    print(f"Chunks: {len(vectors)}")
    print(f"Source: {os.path.basename(pdf_path)}\n")
    
    return doc_id


def ingest_directory(directory_path: str) -> List[str]:
    """
    Ingest all PDF files from a directory.
    
    Args:
        directory_path: Path to directory containing PDFs
        
    Returns:
        List of document IDs that were ingested
    """
    if not os.path.isdir(directory_path):
        raise ValueError(f"Directory not found: {directory_path}")
    
    pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"⚠️  No PDF files found in {directory_path}")
        return []
    
    print(f"\n{'#'*60}")
    print(f"# BATCH INGESTION")
    print(f"{'#'*60}")
    print(f"Directory: {directory_path}")
    print(f"Found {len(pdf_files)} PDF files\n")
    
    doc_ids = []
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(directory_path, pdf_file)
        print(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_file}")
        
        try:
            doc_id = ingest_pdf(pdf_path)
            doc_ids.append(doc_id)
        except Exception as e:
            print(f"❌ Error processing {pdf_file}: {e}")
            continue
    
    print(f"\n{'#'*60}")
    print(f"# BATCH COMPLETE")
    print(f"{'#'*60}")
    print(f"Successfully ingested: {len(doc_ids)}/{len(pdf_files)} files\n")
    
    return doc_ids


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("PDF Ingestion Script for Pinecone Vector Database")
        print("=" * 60)
        print("\nUsage:")
        print("  Single file:")
        print("    python ingest_pdfs.py <path_to_pdf> [doc_id]")
        print("\n  Directory (batch):")
        print("    python ingest_pdfs.py --dir <directory_path>")
        print("\nExamples:")
        print("  python ingest_pdfs.py ./documents/report.pdf")
        print("  python ingest_pdfs.py ./documents/report.pdf my_custom_id")
        print("  python ingest_pdfs.py --dir ./documents/")
        print("\nConfiguration:")
        print(f"  Embedding Model: {EMBEDDING_MODEL}")
        print(f"  Chunk Size: {CHUNK_SIZE} characters")
        print(f"  Chunk Overlap: {CHUNK_OVERLAP} characters")
        sys.exit(0)
    
    # Directory mode
    if sys.argv[1] == "--dir":
        if len(sys.argv) < 3:
            print("❌ Error: Directory path required")
            print("Usage: python ingest_pdfs.py --dir <directory_path>")
            sys.exit(1)
        
        directory_path = sys.argv[2]
        ingest_directory(directory_path)
    
    # Single file mode
    else:
        pdf_path = sys.argv[1]
        doc_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        if not os.path.exists(pdf_path):
            print(f"❌ Error: File not found: {pdf_path}")  
            sys.exit(1)
        
        ingest_pdf(pdf_path, doc_id)


if __name__ == "__main__":
    main()
