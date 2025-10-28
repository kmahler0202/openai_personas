"""
generate_personas.py
-------------------
Complete persona and buyer ecosystem generation pipeline.

Runs a multi-stage AI analysis to produce comprehensive market intelligence reports.
"""

from __future__ import annotations

from openai import OpenAI
from openai.types import responses
import os
import datetime
import time
from typing import Dict, Any, Tuple

from google import genai
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

from services import get_google_services, upload_markdown_to_doc, share_document, send_google_doc_email

# ==============================================================
# Initialize Clients
# ==============================================================

client = OpenAI()
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

model = "gpt-5-mini"


# ==============================================================
# Helper Functions
# ==============================================================

def run_with_tools(system_prompt: str, user_prompt: str) -> Tuple[str, float]:
    """
    Sends a message to GPT-5 with native web_search tool access.
    Returns the model's textual reply and cost.
    """
    response = client.responses.create(
        model=model,
        tools=[{"type": "web_search"}],
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
    )
    node_cost = get_cost_for_node(response)
    return response.output_text, node_cost


def run_gemini_final(system_prompt: str, user_prompt: str) -> str:
    """
    Call Gemini 2.5 Pro to do the final consolidation.
    """
    response = gemini_client.models.generate_content(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt),
        contents=user_prompt
    )
    return response.text


def get_cost_for_node(response: responses.Response) -> float:
    """
    Returns the cost for a given node based on token usage.
    """
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens

    if model == "gpt-5":
        return (input_tokens * 0.00000125) + (output_tokens * 0.00001)
    elif model == "gpt-5-mini":
        return (input_tokens * 0.00000025) + (output_tokens * 0.000002)
    return 0.0


# ==============================================================
# Analysis Nodes
# ==============================================================

def node_industry_scope(state: dict) -> dict:
    """Industry scope analysis node."""
    sys_prompt = f"""
    Map out the structure and dynamics of the {state.get("product_category")} industry selling into the 
    {state.get("target_market_segments")} market segments in {state.get("target_geographies")}.
    Include the size of the industry as well as the major competitors selling these products and services. 
    Include any regulatory issues, the top 3-5 challenges influences the purchase of {state.get("product_category")} for {state.get("target_market_segments")}.

    Expected Output:
    1–2 page brief on the industry context in markdown format. Include sources and incorporate tables as needed.
    """

    user_prompt = "Create the brief now. Use the web_search tool to find relevant and current information. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"industry_scope_md": result}


def node_map_stakeholders(state: dict) -> dict:
    """Stakeholder mapping node."""
    sys_prompt = f"""
    Identify 3-5 key personas (job roles) in {state.get("target_market_segments")} who influence 
    or decide on {state.get("product_category")} purchases. For each persona include:
    - Job title & typical level
    - Key responsibilities
    - Primary pain points
    - Where they typically sit in the decision process (evaluator/influencer/decision-maker/user)

    Expected Output:
    Brief persona summary (markdown format), 1 page total covering all stakeholders.
    """

    user_prompt = "Create the stakeholder map now using web_search as needed. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"stakeholders_md": result}


def node_motivations_kpis(state: dict) -> dict:
    """Motivations and KPIs analysis node."""
    sys_prompt = f"""
    For each persona identified in the {state.get("target_market_segments")} segments, list:
    - Their top 2-3 motivations when evaluating {state.get("product_category")}
    - The key KPIs or metrics they care about (e.g., ROI, time savings, compliance, user satisfaction)

    Expected Output:
    Concise list per persona (markdown), approximately half a page total.
    """

    user_prompt = "Create the motivations & KPIs analysis using web_search. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"motivations_md": result}


def node_watering_holes(state: dict) -> dict:
    """Information sources analysis node."""
    sys_prompt = f"""
    Identify the top information sources (blogs, forums, LinkedIn groups, industry publications, 
    conferences, podcasts, etc.) for {state.get("target_market_segments")} professionals researching {state.get("product_category")}.

    Expected Output:
    Bulleted or tabular list (markdown) grouped by channel type, about half a page.
    """

    user_prompt = "Create the watering holes / information sources list using web_search. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"watering_holes_md": result}


def node_buyer_journey(state: dict) -> dict:
    """Buyer journey mapping node."""
    sys_prompt = f"""
    Map the typical buyer journey for {state.get("target_market_segments")} when purchasing {state.get("product_category")}:
    - Awareness stage: how they learn about the problem
    - Consideration stage: how they evaluate solutions
    - Decision stage: final criteria and approval processes
    
    Expected Output:
    Stage-by-stage breakdown (markdown), about 1 page.
    """

    user_prompt = "Create the buyer journey map using web_search. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"buyer_journey_md": result}


def content_opportunities(state: dict) -> dict:
    """Content opportunities analysis node."""
    sys_prompt = f"""
    Based on the personas, their pain points, and the buyer journey for {state.get("product_category")} 
    in {state.get("target_market_segments")}, suggest 5-7 high-impact content ideas (e.g., blog posts, 
    whitepapers, webinars, case studies) that would resonate at different stages.

    Expected Output:
    Brief content ideas list (markdown), about half a page.
    """

    user_prompt = "Create the content opportunities list using web_search. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"content_opportunities_md": result}


def node_competitor_benchmark_report(state: dict) -> dict:
    """Competitor benchmark analysis node."""
    sys_prompt = f"""
    Research 3-5 competitors offering {state.get("product_category")} to {state.get("target_market_segments")}.
    For each competitor, provide:
    - Company name
    - Key product/service offerings
    - Market positioning and strengths
    - Notable weaknesses or gaps

    Expected Output:
    Competitor comparison (markdown table or bulleted format), about 1 page.
    """

    user_prompt = "Create the competitor benchmark report using web_search. Generate in markdown."

    result, cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += cost

    return {"competitor_benchmark_report_md": result}


def node_final_review(state: dict) -> dict:
    """Final consolidation and review using Gemini."""
    sys_prompt = f"""
    You are a senior market intelligence analyst. Below are research outputs covering:
    1) Industry Scope
    2) Key Stakeholders
    3) Motivations & KPIs
    4) Information Sources (Watering Holes)
    5) Buyer Journey
    6) Content Opportunities
    7) Competitor Benchmark

    Your task:
    - Consolidate these sections into a single, cohesive report
    - Fix any markdown formatting issues
    - Add an executive summary at the top (3-5 bullet points)
    - Ensure all headings are properly formatted (use # for main sections)
    - Make sure tables are properly formatted if present
    - Add a conclusion section summarizing key takeaways

    The final report should be well-structured, professional, and ready to present to {state.get("client")}.
    """

    user_prompt = f"""
    Consolidate the following research outputs into a final report:

    ## Industry Scope
    {state.get('industry_scope_md', 'N/A')}

    ## Key Stakeholders
    {state.get('stakeholders_md', 'N/A')}

    ## Motivations & KPIs
    {state.get('motivations_md', 'N/A')}

    ## Information Sources (Watering Holes)
    {state.get('watering_holes_md', 'N/A')}

    ## Buyer Journey
    {state.get('buyer_journey_md', 'N/A')}

    ## Content Opportunities
    {state.get('content_opportunities_md', 'N/A')}

    ## Competitor Benchmark
    {state.get('competitor_benchmark_report_md', 'N/A')}

    Create the final consolidated report now in markdown format.
    """

    result = run_gemini_final(sys_prompt, user_prompt)

    return {"final_review_md": result}


# ==============================================================
# Main Pipeline Function
# ==============================================================

def run_persona_generation(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete persona generation pipeline.
    
    This function orchestrates all analysis nodes, generates a comprehensive report,
    uploads it to Google Docs, and emails it to the user.
    
    Args:
        form_data: Dictionary containing:
            - product_category (str): Product/service category
            - target_market_segments (str): Target market segments
            - target_geographies (str): Geographic targets
            - client (str): Client name
            - email (str): Recipient email address
    
    Returns:
        dict: Result containing:
            - success (bool): Whether generation succeeded
            - doc_id (str): Google Doc ID (if successful)
            - doc_link (str): Google Doc URL (if successful)
            - error (str): Error message (if failed)
    """
    try:
        start_time = time.time()
        
        # Initialize state
        state = {
            "product_category": form_data.get("product_category"),
            "target_market_segments": form_data.get("target_market_segments"),
            "target_geographies": form_data.get("target_geographies"),
            "client": form_data.get("client"),
            "email": form_data.get("email"),
            "total_cost": 0.0,
            "model_used": model
        }
        
        print('Starting persona generation pipeline...')
        
        # Run all analysis nodes sequentially
        print("Running Industry Scope...")
        result = node_industry_scope(state)
        state["industry_scope_md"] = result["industry_scope_md"]
        
        print("Running Stakeholder Map...")
        result = node_map_stakeholders(state)
        state["stakeholders_md"] = result["stakeholders_md"]
        
        print("Running Motivations & KPIs...")
        result = node_motivations_kpis(state)
        state["motivations_md"] = result["motivations_md"]
        
        print("Running Watering Holes...")
        result = node_watering_holes(state)
        state["watering_holes_md"] = result["watering_holes_md"]
        
        print("Running Buyer Journey...")
        result = node_buyer_journey(state)
        state["buyer_journey_md"] = result["buyer_journey_md"]
        
        print("Running Content Opportunities...")
        result = content_opportunities(state)
        state["content_opportunities_md"] = result["content_opportunities_md"]
        
        print("Running Competitor Benchmark...")
        result = node_competitor_benchmark_report(state)
        state["competitor_benchmark_report_md"] = result["competitor_benchmark_report_md"]
        
        print("Running Final Review & Consolidation...")
        result = node_final_review(state)
        state["final_review_md"] = result["final_review_md"]
        
        # Calculate runtime
        end_time = time.time()
        elapsed_seconds = end_time - start_time
        minutes, seconds = divmod(elapsed_seconds, 60)
        state["runtime_human"] = f"{int(minutes)} minutes {int(seconds)} seconds"
        
        # Generate document title
        today = datetime.date.today()
        formatted_date = today.strftime("%m/%d/%Y")
        doc_title = f"{state['client']} AI-GEN Persona Report {formatted_date}"
        
        # Upload to Google Docs
        print("Uploading to Google Docs...")
        docs_service, drive_service, gmail_service = get_google_services()
        
        doc = upload_markdown_to_doc(
            drive_service=drive_service,
            md_content=state["final_review_md"],
            title=doc_title
        )
        
        # Share with recipient
        if state["email"]:
            print(f"Sharing with {state['email']}...")
            share_document(
                drive_service=drive_service,
                file_id=doc['id'],
                recipient_email=state["email"]
            )
            
            # Send email notification
            print("Sending email notification...")
            send_google_doc_email(
                gmail_service=gmail_service,
                recipient_email=state["email"],
                doc_link=doc['webViewLink'],
                doc_id=doc['id'],
                state=state
            )
        
        print("✅ Persona generation complete!")
        
        return {
            "success": True,
            "doc_id": doc['id'],
            "doc_link": doc['webViewLink']
        }
        
    except Exception as e:
        print(f"❌ Persona generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
