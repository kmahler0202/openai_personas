"""
rfp_answer.py
Answer RFP questions using RAG (Retrieval-Augmented Generation) with Pinecone vector database.
Takes questions extracted from RFP breakdown and answers them one by one with relevant context.
"""

import os
import sys
import time
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
TOP_K = 10  # Number of context chunks to retrieve per question


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
    
    system_prompt = """You are a strategic proposal writer for The MX Group, a B2B marketing agency that blends deep industry expertise with pragmatic creativity.

                        Your role is to craft clear, persuasive, and authentic responses to RFP (Request for Proposal) questions using only the information provided.

                        Write in a tone that reflects The MX Group’s voice:
                        - Confident but not overpromising
                        - Professional, plainspoken, and easy to follow
                        - Client-focused, showing understanding of business challenges and solutions
                        - Organized and thoughtful — responses should flow naturally, not read like bullet points from an AI

                        Your responsibilities:
                        1. Use only the provided context to answer each RFP question — do not invent or assume facts.
                        2. Where relevant, connect information into a cohesive narrative rather than listing fragments.
                        3. Use full sentences and natural transitions to sound like a human expert, not a system.
                        4. If something isn’t addressed in the context, state that directly and professionally.
                        5. Keep the response polished, clear, and reflective of MX Group’s expertise in marketing strategy, technology, and implementation.
                    """

    user_prompt = f"""Below is background material from The MX Group’s internal sources that may help answer a client’s RFP question:

**RFP Question:**
{question}

**Context from relevant documents:**

{formatted_context}

Write a response to this RFP question that:
- Uses only information found in the provided context
- Reflects The MX Group’s authentic tone and perspective
- Reads naturally, as if written by an experienced proposal writer
- Is organized clearly, with logical flow and client-focused framing
- Acknowledges any missing or incomplete information transparently

**Proposed Response:**"""

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


def answer_rfp_questions(questions: List[str], top_k: int = TOP_K) -> Dict[str, Any]:
    """
    Answer multiple RFP questions using RAG.
    
    Args:
        questions: List of RFP questions to answer
        top_k: Number of context chunks to retrieve per question
        
    Returns:
        Dictionary with answers and metadata
    """
    start_time = time.time()
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
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED: Answered {len(answers)}/{len(questions)} questions")
    print(f"{'='*80}\n")
    
    return {
        "answers": answers,
        "metadata": {
            "start_time": start_time,
            "end_time": end_time,
            "elapsed_time": elapsed_time,
            "questions_answered": len(answers),
            "total_questions": len(questions)
        }
    }


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


def save_answers_to_file(answers: Dict[str, Any], output_path: str):
    """Save answers to a text file."""
    formatted_output = format_answers_for_output(answers["answers"])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatted_output)
    
    print(f"✅ Answers saved to: {output_path}")
