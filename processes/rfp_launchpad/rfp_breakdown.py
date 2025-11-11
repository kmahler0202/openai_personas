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

MODEL = "gpt-5" 
    

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

Your purpose is not only to pull out information from the RFP — your primary goal is to prepare all vendor questions in a format that maximizes accuracy during later vector database retrieval.

SPECIAL RULES FOR QUESTIONS:
    -Every question returned must be standalone and contain all necessary contextual information inside the question itself.
    -Do not produce vague questions that rely on earlier or external sections.
    -If a question references another section (ex: “see section 3.1 for required services”), you must locate that referenced content inside the RFP and append/inline the relevant information directly into the question so the question can be answered independently later.
    -Do not include identity assumptions about who “we” or the vendor is — stay vendor neutral and non-personalized.
    -DO NOT EVER include the client/prospect's name in the question. It hurts our RAG accuracy to have it as a keyword. Even if in their question they say their companies name, you should remove it.
    -Only include real explicit prospect questions. Do not include “intent to bid” confirmations, form filling instructions, or requests for digital files/assets.
    -Include 'The Mx Group' in every question that is asked in the RFP. For example, if the RFP asks "What is your approach to a marketing campaign?", the question should be rephrased to "What is The Mx Group's approach to a marketing campaign?". You can follow a similar pattern for other questions. 
    -Do not add any additional information to the question that is not explicity stated in the RFP's question, except for the 'The Mx Group' addition as well as adding explictly referenced context, as said above.

The overall objective is: maximize future retrieval accuracy by converting questions into fully contextualized, atomic, standalone queries.

Return output in strict JSON schema format (keys listed below).

Return your analysis as a JSON object with these exact keys:
- company_name
- company_overview
- objective
- scope_of_work
- questions_to_answer

For each category, provide a clear, well-organized summary of the relevant information found in the document. If a category has no relevant information, state "Not specified in the document."
"""

    user_prompt = f"""Please analyze this RFP document and provide the following information taken from the document:

1. **Company Name**: The name of the company who has sent over the RFP to our agency.
2. **Company Overview**: A brief overview of the company, including their history, current situation, and contextual information. Summarize the information from the RFP into a simple paragraph here.
3. **Objective**: What they're trying to achieve, problems they're solving, goals and desired outcomes
4. **Scope of Work**: Specific work to be performed, deliverables, project scope, technical requirements.
5. **Questions That Need to Be Answered**: The specific questions that are posed to our agency. These questions should be phrased in a way that maximizes retrival accuracy. For example, each and every questions should be rephrased to be vendor-neutral while containing the name of our agency, The Mx Group.
    - For example, say we are responding to an RFP from company X, and they ask the question "What is would your approach to a marketing campaign be for company X?". The question should be rephrased to "What kind of approach would The Mx Group take in a marketing campaign?"
    - Additionally, some questions make direct references to other areas in the RFP. For example, if the RFP has a section titled "Statement of Need" which maps out services that they want their agency to have, and a specific question asks "Is your agency able to provide the services outline in the statement of need", the correct rephrasing would be "Is The Mx Group able to provide the services listed here: (with then the services form the statement of need section appended here)
    - To maximize retrieval accuracy, questions should always stay separate from eachother, and no matter how similar two questions may be, they should not ever be combined into a single question.

Here is the RFP document:

{pdf_text}

Provide your analysis in JSON format with the keys: company_name, company_overview, objective, scope_of_work, questions_to_answer
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
                            "company_name": {
                                "type": "string",
                            },
                            "company_overview": {
                                "type": "string",
                            },
                            "objective": {
                                "type": "string",
                            },
                            "scope_of_work": {
                                "type": "string",
                            },
                            "questions_to_answer": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": [
                            "company_name",
                            "company_overview",
                            "objective",
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
        "company_name": "1. COMPANY NAME",
        "company_overview": "2. COMPANY OVERVIEW",
        "objective": "3. OBJECTIVE",
        "scope_of_work": "4. SCOPE OF WORK",
        "questions_to_answer": "5. QUESTIONS THAT NEED TO BE ANSWERED"
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
