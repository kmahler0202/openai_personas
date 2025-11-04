"""
rfp_answer.py
Answer RFP questions using RAG (Retrieval-Augmented Generation) with Pinecone vector database.
Takes questions extracted from RFP breakdown and answers them one by one with relevant context.
"""

import os
import sys
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

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
RESPONSE_MODEL = "gpt-5-mini"
TOP_K = 5  # Number of context chunks to retrieve per question


def generate_query_embedding(query: str) -> List[float]:
    """Generate embedding for a question."""
    response = client.embeddings.create(
        input=query,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def retrieve_context(query: str, top_k: int = TOP_K) -> List[Dict]:
    """
    Retrieve relevant context from Pinecone vector database.
    
    Args:
        query: Question to find context for
        top_k: Number of chunks to retrieve
        
    Returns:
        List of relevant context chunks with metadata
    """
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
    
    return context_chunks


def format_context(context_chunks: List[Dict]) -> str:
    """Format retrieved context for the prompt."""
    formatted = []
    for i, chunk in enumerate(context_chunks, 1):
        formatted.append(f"[Context {i} - {chunk['source']} (relevance: {chunk['score']:.3f})]")
        formatted.append(chunk['text'])
        formatted.append("")  # Empty line between chunks
    
    return "\n".join(formatted)


def answer_single_question(question: str, top_k: int = TOP_K) -> Dict[str, Any]:
    """
    Answer a single RFP question using RAG.
    
    Args:
        question: The RFP question to answer
        top_k: Number of context chunks to retrieve
        
    Returns:
        Dictionary with question, answer, context, and sources
    """
    print(f"\n📋 Question: {question}")
    print(f"🔍 Retrieving relevant context...")
    
    # Step 1: Retrieve context
    context_chunks = retrieve_context(question, top_k)
    
    if not context_chunks:
        print("⚠️  No relevant context found")
        return {
            "question": question,
            "answer": "Unable to find relevant information in the knowledge base to answer this question.",
            "context_chunks": [],
            "sources": [],
            "confidence": "low"
        }
    
    print(f"✅ Retrieved {len(context_chunks)} relevant chunks")
    
    # Step 2: Format context
    formatted_context = format_context(context_chunks)
    
    # Step 3: Generate answer using OpenAI
    print(f"🤖 Generating answer...")
    
    system_prompt = """You are an expert assistant helping to respond to RFP (Request for Proposal) questions.

Your task is to:
1. Answer the RFP question using ONLY the information provided in the context
2. Provide detailed, professional, and well-structured answers
3. If the context contains relevant information, synthesize it into a comprehensive response
4. If the context doesn't contain enough information, clearly state what's missing
5. Cite sources when relevant (e.g., "According to [source name]...")
6. Be specific and include relevant details, examples, and methodologies when available
7. Structure your answer with clear paragraphs or bullet points as appropriate"""

    user_prompt = f"""Based on the following context from our company's documents and materials, please answer this RFP question:

**RFP Question:**
{question}

**Context from relevant documents:**

{formatted_context}

**Instructions:**
- Provide a comprehensive, professional answer
- Use only information from the provided context
- Structure your response clearly
- If information is insufficient, state what's missing

**Answer:**"""

    response = client.chat.completions.create(
        model=RESPONSE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
    )
    
    answer = response.choices[0].message.content.strip()
    print(f"✅ Answer generated\n")
    
    # Extract unique sources
    sources = {}
    for chunk in context_chunks:
        source = chunk['source']
        if source not in sources:
            sources[source] = chunk['score']
    
    # Determine confidence based on relevance scores
    avg_score = sum(chunk['score'] for chunk in context_chunks) / len(context_chunks)
    confidence = "high" if avg_score > 0.8 else "medium" if avg_score > 0.6 else "low"
    
    return {
        "question": question,
        "answer": answer,
        "context_chunks": context_chunks,
        "sources": list(sources.keys()),
        "confidence": confidence,
        "avg_relevance_score": avg_score
    }


def answer_rfp_questions(questions: List[str], top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Answer multiple RFP questions using RAG.
    
    Args:
        questions: List of RFP questions to answer
        top_k: Number of context chunks to retrieve per question
        
    Returns:
        List of answer dictionaries, one per question
    """
    print(f"\n{'='*80}")
    print(f"RFP QUESTION ANSWERING SYSTEM")
    print(f"{'='*80}")
    print(f"Total questions to answer: {len(questions)}")
    print(f"Model: {RESPONSE_MODEL}")
    print(f"Context chunks per question: {top_k}\n")
    
    answers = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─'*80}")
        print(f"Question {i}/{len(questions)}")
        print(f"{'─'*80}")
        
        try:
            result = answer_single_question(question, top_k)
            answers.append(result)
            
            # Display answer summary
            print(f"\n💡 Answer:")
            print(f"{result['answer']}")
            print(f"\n📚 Sources: {', '.join(result['sources'])}")
            print(f"🎯 Confidence: {result['confidence']}")
            
        except Exception as e:
            print(f"❌ Error answering question: {e}")
            answers.append({
                "question": question,
                "answer": f"Error generating answer: {str(e)}",
                "context_chunks": [],
                "sources": [],
                "confidence": "error"
            })
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED: Answered {len(answers)}/{len(questions)} questions")
    print(f"{'='*80}\n")
    
    return answers


def format_answers_for_output(answers: List[Dict[str, Any]]) -> str:
    """Format answers into a readable text output."""
    output = []
    output.append("="*80)
    output.append("RFP QUESTIONS & ANSWERS")
    output.append("="*80)
    output.append("")
    
    for i, result in enumerate(answers, 1):
        output.append(f"\n{'─'*80}")
        output.append(f"QUESTION {i}")
        output.append(f"{'─'*80}")
        output.append(f"\n{result['question']}\n")
        output.append(f"ANSWER:")
        output.append(f"{result['answer']}\n")
        output.append(f"Sources: {', '.join(result['sources'])}")
        output.append(f"Confidence: {result['confidence']}")
        
        if result.get('avg_relevance_score'):
            output.append(f"Avg Relevance Score: {result['avg_relevance_score']:.3f}")
        output.append("")
    
    return "\n".join(output)


def save_answers_to_file(answers: List[Dict[str, Any]], output_path: str):
    """Save answers to a text file."""
    formatted_output = format_answers_for_output(answers)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatted_output)
    
    print(f"✅ Answers saved to: {output_path}")
