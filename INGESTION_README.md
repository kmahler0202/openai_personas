# PDF Ingestion Script

Simple script to ingest PDF documents into your Pinecone vector database.

## Setup

```bash
pip install -r requirements.txt
```

Ensure your `.env` file has:
```
PINECONE_API_KEY=your_key
OPENAI_API_KEY=your_key
```

## Usage

### Ingest a Single PDF

```bash
python ingest_pdfs.py path/to/document.pdf
```

With custom document ID:
```bash
python ingest_pdfs.py path/to/document.pdf my_custom_id
```

### Ingest All PDFs in a Directory

```bash
python ingest_pdfs.py --dir path/to/documents/
```

## What It Does

1. **Extracts text** from PDF using PyPDF2
2. **Chunks text** into 1000-character pieces with 200-character overlap
3. **Generates embeddings** using OpenAI's `text-embedding-3-small` (1536 dimensions)
4. **Uploads to Pinecone** with metadata (source, chunk_id, text preview)

## Example Output

```
============================================================
📄 INGESTING PDF
============================================================
File: ./documents/report.pdf
Doc ID: report_20241031_101500

🔄 Extracting text from PDF...
✅ Extracted 15,234 characters
🔄 Chunking text (size=1000, overlap=200)...
✅ Created 18 chunks
🔄 Generating embeddings...
✅ Generated 18 embeddings
🔄 Preparing vectors for Pinecone...
✅ Prepared 18 vectors
🔄 Uploading to Pinecone...
✅ Upserted 18 vectors into 'rfp-corpus'.

============================================================
✅ INGESTION COMPLETE
============================================================
Doc ID: report_20241031_101500
Chunks: 18
Source: report.pdf
```

## Configuration

Edit these constants in `ingest_pdfs.py`:

```python
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks
```

## Use in Code

```python
from ingest_pdfs import ingest_pdf, ingest_directory

# Ingest single file
doc_id = ingest_pdf("./documents/report.pdf")

# Ingest directory
doc_ids = ingest_directory("./documents/")
```

## Querying Ingested Documents

After ingestion, query your documents:

```python
from services.pinecone_db import query_vector
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Generate query embedding
query_text = "What are the key requirements?"
response = client.embeddings.create(
    input=query_text,
    model="text-embedding-3-small"
)
query_embedding = response.data[0].embedding

# Search Pinecone
results = query_vector(query_embedding, top_k=5)

# Display results
for match in results.matches:
    print(f"Score: {match.score:.4f}")
    print(f"Source: {match.metadata['source']}")
    print(f"Text: {match.metadata['text'][:200]}...")
    print()
```

## Notes

- Document IDs are auto-generated as `{filename}_{timestamp}` if not provided
- Text chunks preserve context with 200-character overlap
- Metadata includes source filename, chunk ID, and text preview
- Batch processing handles errors gracefully and continues with remaining files
