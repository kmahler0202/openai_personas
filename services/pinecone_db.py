"""
pinecone_db.py
Service layer for connecting to Pinecone, creating the index if needed,
and exposing simple helper functions for upsert/query operations.
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

# ---------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("❌ Missing PINECONE_API_KEY in .env file")

# ---------------------------------------------------------------------
# Pinecone client and index setup
# ---------------------------------------------------------------------
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "rfp-corpus"

# Check if the index exists; if not, create it
existing_indexes = [idx["name"] for idx in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    print(f"🪄 Creating Pinecone index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536,  # matches text-embedding-3-large
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
else:
    print(f"✅ Pinecone index '{INDEX_NAME}' already exists.")

# Get a handle to the index
index = pc.Index(INDEX_NAME)

# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def upsert_vectors(vectors):
    """
    Upsert vectors into the Pinecone index.
    vectors: list of dicts with keys: id, values, metadata
    """
    index.upsert(vectors=vectors)
    print(f"✅ Upserted {len(vectors)} vectors into '{INDEX_NAME}'.")


def query_vector(vector, top_k=5, include_metadata=True):
    """
    Query the Pinecone index by vector similarity.
    """
    results = index.query(vector=vector, top_k=top_k, include_metadata=include_metadata)
    return results


def delete_index():
    """Deletes the current index (use with caution)."""
    pc.delete_index(INDEX_NAME)
    print(f"🗑️ Deleted index '{INDEX_NAME}'.")
