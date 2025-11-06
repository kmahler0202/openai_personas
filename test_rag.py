"""
test_rag.py
Test script for Retrieval-Augmented Generation (RAG) using Pinecone vector database.
Uses OpenAI Responses API for answer generation.
"""

import os
import sys
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from services.pinecone_db import query_vector

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
RESPONSE_MODEL = "gpt-4o-mini"  # or "gpt-4o" for better quality
TOP_K = 20  # Number of context chunks to retrieve


def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for the user's question."""
    response = client.embeddings.create(
        input=query,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def retrieve_context(query: str, top_k: int = TOP_K) -> List[Dict]:
    """
    Retrieve relevant context from Pinecone vector database.
    
    Args:
        query: User's question
        top_k: Number of chunks to retrieve
        
    Returns:
        List of relevant context chunks with metadata
    """
    print(f"🔍 Searching vector database...")
    
    # Generate embedding for query
    query_embedding = generate_query_embedding(query)
    
    # Query Pinecone
    results = query_vector(query_embedding, top_k=top_k, include_metadata=True)
    
    # Extract context chunks
    context_chunks = []
    for match in results.matches:
        context_chunks.append({
            "text": match.metadata.get("text", ""),
            "source": match.metadata.get("source", "unknown"),
            "doc_id": match.metadata.get("doc_id", "unknown"),
            "score": float(match.score)
        })
    
    print(f"✅ Retrieved {len(context_chunks)} relevant chunks\n")
    return context_chunks


def format_context(context_chunks: List[Dict]) -> str:
    """Format retrieved context for the prompt."""
    formatted = []
    for i, chunk in enumerate(context_chunks, 1):
        formatted.append(f"[Source {i}: {chunk['source']} (relevance: {chunk['score']:.3f})]")
        formatted.append(chunk['text'])
        formatted.append("")  # Empty line between chunks
    
    return "\n".join(formatted)


def generate_answer(query: str, context: str) -> str:
    """
    Generate answer using OpenAI Responses API with retrieved context.
    
    Args:
        query: User's question
        context: Retrieved context from vector database
        
    Returns:
        Generated answer
    """
    print(f"🤖 Generating answer with {RESPONSE_MODEL}...")
    
    prompt = f"""You are a helpful assistant that answers questions based on the provided context from RFP documents and marketing materials.

Instructions:
- Answer the question using ONLY the information provided in the context
- If the context contains relevant information, provide a detailed and well-structured answer
- If the context doesn't contain enough information to answer the question, say so clearly
- Cite which sources you're using when relevant (e.g., "According to Source 1...")
- Be professional and concise
- If multiple sources provide similar information, synthesize them into a coherent answer

Context from relevant documents:

{context}

---

Question: {query}

Answer:"""

    response = client.completions.create(
        model=RESPONSE_MODEL,
        prompt=prompt,
        temperature=0.7,
        max_tokens=1000
    )
    
    answer = response.choices[0].text.strip()
    print(f"✅ Answer generated\n")
    
    return answer


def rag_query(query: str, top_k: int = TOP_K, show_context: bool = False) -> Dict:
    """
    Complete RAG pipeline: retrieve context and generate answer.
    
    Args:
        query: User's question
        top_k: Number of context chunks to retrieve
        show_context: Whether to display retrieved context
        
    Returns:
        Dictionary with answer, context, and metadata
    """
    print(f"\n{'='*80}")
    print(f"RAG QUERY")
    print(f"{'='*80}")
    print(f"Question: {query}\n")
    
    # Step 1: Retrieve context
    context_chunks = retrieve_context(query, top_k)
    
    if not context_chunks:
        print("❌ No relevant context found in vector database")
        return {
            "query": query,
            "answer": "I couldn't find any relevant information in the database to answer this question.",
            "context": [],
            "sources": []
        }
    
    # Step 2: Format context
    formatted_context = format_context(context_chunks)
    
    # Step 3: Generate answer
    answer = generate_answer(query, formatted_context)
    
    # Display results
    print(f"{'='*80}")
    print(f"ANSWER")
    print(f"{'='*80}")
    print(answer)
    print()
    
    # Show sources
    print(f"{'='*80}")
    print(f"SOURCES")
    print(f"{'='*80}")
    sources = {}
    for chunk in context_chunks:
        source = chunk['source']
        if source not in sources:
            sources[source] = chunk['score']
    
    for i, (source, score) in enumerate(sources.items(), 1):
        print(f"{i}. {source} (relevance: {score:.3f})")
    print()
    
    # Optionally show retrieved context
    if show_context:
        print(f"{'='*80}")
        print(f"RETRIEVED CONTEXT")
        print(f"{'='*80}")
        for i, chunk in enumerate(context_chunks, 1):
            print(f"\n--- Chunk {i} (score: {chunk['score']:.3f}) ---")
            print(f"Source: {chunk['source']}")
            print(f"Text: {chunk['text'][:300]}...")
        print()
    
    return {
        "query": query,
        "answer": answer,
        "context": context_chunks,
        "sources": list(sources.keys())
    }


def interactive_mode():
    """Interactive mode for asking multiple questions."""
    print(f"\n{'#'*80}")
    print(f"# RAG INTERACTIVE MODE")
    print(f"{'#'*80}")
    print(f"Ask questions about your ingested documents.")
    print(f"Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            query = input("Question: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not query:
                continue
            
            rag_query(query)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("RAG Test Script - Query your vector database with AI")
        print("=" * 80)
        print("\nUsage:")
        print("  Single question:")
        print('    python test_rag.py "Your question here"')
        print("\n  Interactive mode:")
        print("    python test_rag.py --interactive")
        print("\n  Show retrieved context:")
        print('    python test_rag.py --context "Your question here"')
        print("\nExamples:")
        print('  python test_rag.py "What steps would your firm follow for an integrated marketing campaign?"')
        print('  python test_rag.py --interactive')
        print('  python test_rag.py --context "What is the approach for marketing campaigns?"')
        print("\nConfiguration:")
        print(f"  Embedding Model: {EMBEDDING_MODEL}")
        print(f"  Response Model: {RESPONSE_MODEL}")
        print(f"  Context Chunks: {TOP_K}")
        sys.exit(0)
    
    # Interactive mode
    if sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
        interactive_mode()
    
    # Show context mode
    elif sys.argv[1] == "--context" or sys.argv[1] == "-c":
        if len(sys.argv) < 3:
            print("❌ Error: Question required")
            print('Usage: python test_rag.py --context "Your question"')
            sys.exit(1)
        
        query = sys.argv[2]
        rag_query(query, show_context=True)
    
    # Single question mode
    else:
        query = sys.argv[1]
        rag_query(query)


if __name__ == "__main__":
    main()
