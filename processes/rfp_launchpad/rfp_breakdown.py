"""
rfp_breakdown.py
Lightweight OpenAI-based RFP breakdown system that categorizes PDF content into 6 key categories.
"""

import os
import sys
from typing import Dict, Optional, List
from pathlib import Path
import PyPDF2
from openai import OpenAI
from dotenv import load_dotenv
import json
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Configuration - using lightweight model
MODEL = "gpt-5-mini"  # Fast and cost-effective
    

def breakdown_rfp(pdf_text: str) -> Dict[str, str]:
    """
    Use OpenAI to break down RFP content into 6 categories.
    
    Categories:
    1. Background & Context
    2. Objectives/Problem Statements
    3. Evaluation Criteria & Decision Logic
    4. Rules/Response Guidelines/Format Instructions
    5. Statement of Need/Scope of Work
    6. Questions That Need to Be Answered
    """
    
    system_prompt = """You are an expert RFP analyst specializing in preparing RFP documents for downstream Retrieval-Augmented Generation (RAG) pipelines.

Your purpose is not only to categorize the RFP — your primary goal is to prepare all vendor questions in a format that maximizes accuracy during later vector database retrieval.

SPECIAL RULES FOR QUESTIONS:
    -Every question returned must be standalone and contain all necessary contextual information inside the question itself.
    -Do not produce vague questions that rely on earlier or external sections.
    -If a question references another section (ex: “see 3.1 for required services”), you must locate that referenced content inside the RFP and append/inline the relevant information directly into the question so the question can be answered independently later.
    -Do not include identity assumptions about who “we” or the vendor is — stay vendor neutral and non-personalized. In other words, no question should include the vendors name.
    -Only include real explicit prospect questions. Do not include “intent to bid” confirmations, form filling instructions, or requests for digital files/assets.

The overall objective is: maximize future retrieval accuracy by converting questions into fully contextualized, atomic, standalone queries.

Return output in strict JSON schema format (keys listed below).

Return your analysis as a JSON object with these exact keys:
- background_and_context
- objectives_and_problems
- evaluation_criteria
- rules_and_guidelines
- scope_of_work
- questions_to_answer

For each category, provide a clear, well-organized summary of the relevant information found in the document. If a category has no relevant information, state "Not specified in the document."
"""

    user_prompt = f"""Please analyze this RFP document and break it down into the following 6 categories:

1. **Background & Context**: Company background, project history, current situation, and contextual information
2. **Objectives/Problem Statements**: What they're trying to achieve, problems they're solving, goals and desired outcomes
3. **Evaluation Criteria & Decision Logic**: How proposals will be evaluated, scoring criteria, decision-making factors, weighting
4. **Rules/Response Guidelines/Format Instructions**: Submission requirements, formatting rules, deadlines, proposal structure requirements
5. **Statement of Need/Scope of Work**: Specific work to be performed, deliverables, project scope, technical requirements
6. **Questions That Need to Be Answered**: Specific questions posed to vendors, information requests, clarifications needed (fully contextualized single questions prepared for RAG retrieval — see system rules above).

Here is the RFP document:

{pdf_text}

Provide your analysis in JSON format with the keys: background_and_context, objectives_and_problems, evaluation_criteria, rules_and_guidelines, scope_of_work, questions_to_answer
Do not repeat the keys in the JSON output."""

    print("🔄 Analyzing RFP with OpenAI...")
    
    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        text={
            "format":{
                "type": "json_schema",
                "name": "rfp_breakdown",
                "schema": {
                        "type": "object",
                        "properties": {
                            "background_and_context": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "objectives_and_problems": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "evaluation_criteria": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "rules_and_guidelines": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "scope_of_work": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "questions_to_answer": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": [
                            "background_and_context",
                            "objectives_and_problems",
                            "evaluation_criteria",
                            "rules_and_guidelines",
                            "scope_of_work",
                            "questions_to_answer"
                        ],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
    )

    result = response.output_text

    parsed_result = json.loads(result)

    print(result)

    print(parsed_result)

    
    return parsed_result


def format_breakdown_output(breakdown: Dict[str, str]) -> str:
    """Format the breakdown results in a readable format."""
    
    category_titles = {
        "background_and_context": "1. BACKGROUND & CONTEXT",
        "objectives_and_problems": "2. OBJECTIVES/PROBLEM STATEMENTS",
        "evaluation_criteria": "3. EVALUATION CRITERIA & DECISION LOGIC",
        "rules_and_guidelines": "4. RULES/RESPONSE GUIDELINES/FORMAT INSTRUCTIONS",
        "scope_of_work": "5. STATEMENT OF NEED/SCOPE OF WORK",
        "questions_to_answer": "6. QUESTIONS THAT NEED TO BE ANSWERED"
    }
    
    output = "\n" + "="*80 + "\n"
    output += "RFP BREAKDOWN ANALYSIS\n"
    output += "="*80 + "\n\n"
    
    for key, title in category_titles.items():
        content = breakdown.get(key, "Not found")
        output += f"{title}\n"
        output += "-"*80 + "\n"
        output += f"{content}\n\n"
    
    return output
