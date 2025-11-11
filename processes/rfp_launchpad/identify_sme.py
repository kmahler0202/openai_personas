"""identify_sme.py
Identifies the best subject matter expert (SME) to answer a given question based on their role and expertise.
"""

import os
import sys
from typing import Dict
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env file")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-5-mini"


# Define available SMEs with their expertise areas
AVAILABLE_SMES = [
    {
        "full_name": "Tony Riley",
        "role": "President & CEO",
        "department": ["Corporate", "Marketing & Sales"],
        "email": "triley@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Erin Puplava",
        "role": "VP, People",
        "department": ["Corporate"],
        "email": "epuplava@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Mita Quadri",
        "role": "VP of Finance & Accounting",
        "department": ["Corporate"],
        "email": "mquadri@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Sarah LaPalomento",
        "role": "Marketing Director",
        "department": ["Marketing & Sales"],
        "email": "slapalomento@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Christian Ambrose",
        "role": "Growth Manager",
        "department": ["Marketing & Sales"],
        "email": "cambrose@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Paul Hirsch",
        "role": "Chief Creative Officer",
        "department": ["Creative", "Strategic Planning"],
        "email": "phirsch@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Kelly Olson",
        "role": "VP of Strategic Planning",
        "department": ["Strategic Planning"],
        "email": "kolson@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Lisa Everett",
        "role": "VP, Managing Director",
        "department": ["Account Management"],
        "email": "leverett@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Pete Baughman",
        "role": "Senior Director of Media",
        "department": ["Activation"],
        "email": "pbaughman@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Brendan Turner",
        "role": "Senior Vice President of Digital Experience",
        "department": ["Digital Experience"],
        "email": "bturner@themxgroup.com",
        "expertise": ""
    },
    {
        "full_name": "Eric Von Zee",
        "role": "VP of Application Development",
        "department": ["Digital Experience"],
        "email": "evonzee@themxgroup.com",
        "expertise": ""
    }
]


def identify_sme(question: str) -> Dict[str, str]:
    """
    Identify the best SME to answer a given question based on their expertise.
    
    Args:
        question: The question that needs to be answered
        
    Returns:
        Dict containing full_name, role, and email of the best-fit SME
    """
    
    # Format SME list for the prompt with indices
    sme_list = "\n".join([
        f"Index {i}: {sme['full_name']} ({sme['role']}) - Department: {', '.join(sme['department'])}"
        for i, sme in enumerate(AVAILABLE_SMES)
    ])
    
    system_prompt = f"""You are an expert at matching questions to the most appropriate subject matter expert (SME) based on their role and area of expertise.

Your task is to analyze the given question and determine which SME from the available list would be best suited to answer it.

Available SMEs:
{sme_list}

Consider the following when making your decision:
- The core topic and domain of the question
- The specific expertise required to provide a comprehensive answer
- The role and responsibilities that align most closely with the question

Return your selection as a JSON object with the index number (0-{len(AVAILABLE_SMES)-1}) of the most appropriate SME."""

    user_prompt = f"""Please identify which SME would be best suited to answer the following question: 

Question: {question}

Return the index number of the most appropriate SME."""

    print("🔄 Identifying best SME with OpenAI...")
    
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
                "name": "sme_identification",
                "schema": {
                    "type": "object",
                    "properties": {
                        "sme_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": len(AVAILABLE_SMES) - 1
                        }
                    },
                    "required": [
                        "sme_index"
                    ],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    )

    result = response.output_text
    parsed_result = json.loads(result)
    
    # Get the index and retrieve the SME directly
    sme_index = parsed_result.get("sme_index")
    
    # Validate index
    if sme_index is None or sme_index < 0 or sme_index >= len(AVAILABLE_SMES):
        raise ValueError(f"❌ Invalid SME index: {sme_index}")
    
    # Get the SME data
    sme = AVAILABLE_SMES[sme_index]
    selected_sme = {
        "full_name": sme["full_name"],
        "role": sme["role"],
        "department": sme["department"],
        "email": sme["email"]
    }
    
    print(f"✅ Selected SME: {selected_sme['full_name']} ({selected_sme['role']})")
    
    return selected_sme