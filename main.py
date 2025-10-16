from __future__ import annotations

from openai import OpenAI
from openai.types import responses
import os

from google import genai
from google.genai import types

from typing import Tuple

import datetime
import time

from dotenv import load_dotenv
load_dotenv()

from md_2_gdoc import full_pipeline as convert_to_gdoc

# ==============================================================
# GPT-5 + Native Web Search Test
# ==============================================================

client = OpenAI()
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

model = "gpt-5-mini"

def run_with_tools(system_prompt: str, user_prompt: str) -> Tuple[str, float]:
    """
    Sends a message to GPT-5 with native web_search tool access.
    Returns the model's textual reply.
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
    Uses the google-generativeai client.
    """
    # Build contents list per Google API format
    response = gemini_client.models.generate_content(
        model="gemini-2.5-pro",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt),
        contents=user_prompt
    )
    
    # resp.text has the generated content
    return response.text

# ==============================================================
# Get cost for Node
# ==============================================================
def get_cost_for_node(response: Response) -> float:
    """
    Returns the cost for a given node.
    """
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens



    if(model == "gpt-5"):
        return (input_tokens * .00000125) + (output_tokens * .00001)
    elif(model == "gpt-5-mini"):
        return (input_tokens * .00000025) + (output_tokens * .000002)


# ==============================================================
# Example Node (Industry Scope)
# ==============================================================

def node_industry_scope(state: dict) -> dict:
    """industry_scoper"""

    sys_prompt = f"""
    Map out the structure and dynamics of the {state.get("product_category")} industry selling into the 
    {state.get("target_market_segments")} market segments in {state.get("target_geographies")}.
    Include the sizeof the industry as well as the major competitors selling these products and services. 
    Include any regulatory issues, the top 3-5 challenges influences the purchase of {state.get("product_category")} for {state.get("target_market_segments")}.

    Expected Output:
    1–2 page brief on the industry context in markdown format. Include sources and incorporate tables as needed.
    """

    user_prompt = (
        "Create the brief now. Use the web_search tool to find relevant and current information. Generate in markdown."
    )

    md, node_cost = run_with_tools(sys_prompt, user_prompt)
    state["total_cost"] += node_cost
    return {"industry_scope_md": md}


def node_map_stakeholders(state: dict) -> dict:
    """stake_holder_mapper"""
    sys_prompt = (
        f"""
        Understanding the industry scoping information, identify the most common decision makers and decision influencers in the purchase of {state.get("product_category")}.
        Map their role, typical titles, where they fit in the process, and the decision weight they bear (economic buyer, technical specifier, user / operator, compliance gatekeeper, etc.).

        Expected Output:
        In markdown, a section for each of the economic buyer, technical specifier, user /operator, compliance gatekeeper, as well as any more that you find relevant. each section should have
        - who they are
        - their typical titles
        - where they fit in the process
        - the decision weight they bear
        """
    )
    user = (
        "INDUSTRY SCOPE BRIEF (Markdown below):\n\n"
        f"{state.get('industry_scope_md')}\n\n"
        "Produce buying committee as specified. Use the web_search tool to find relevant information."
    )
    md, node_cost = run_with_tools(sys_prompt, user)
    state["total_cost"] += node_cost
    return {"stakeholders_md": md}  

def node_motivations_kpis(state: dict) -> dict:
    """motivator_and_kpi_analyst"""
    sys_prompt = (
        f"""
        For each of the roles in the buying committee, show what each role cares about most--their business drivers, risk concerns, and success metrics.

        Expected Output:
        In Markdown, a table of key motivations, risks and concerns, and typical KPIs for each role.
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\n Use the industry scope and buying committee as context. Use the web_search tool to find relevant information."
    )
    md, node_cost = run_with_tools(sys_prompt, user)
    state["total_cost"] += node_cost
    return {"motivations_md": md}

def node_watering_holes(state: dict) -> dict:
    """information_source_analyst"""
    sys_prompt = (
        f"""
        For each role defined in the buying committee, research where each stakeholder goes for insight: media, analyst firms, standards bodies, trade associations, events, and digital channels.
        

        Expected Output:
        In Markdown, Deliver a channel map per role (preferred trade pubs, conferences, online forums, social media platforms, newsletters, associations) Do not do this in a table.
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\nMOTIVATIONS & KPIs:\n" + state.get("motivations_md", "(missing)") +
        "\n\nCreate the channel map. Use the web_search tool to find relevant information."
    )
    md, node_cost = run_with_tools(sys_prompt, user)
    state["total_cost"] += node_cost
    return {"watering_holes_md": md}

def node_buyer_journey(state: dict) -> dict:
    """buying_journey_analyst"""
    sys_prompt = (
        f"""
        For the core buying unit and for other defined decision influencers, outline how these roles interact through the typical buying cycle,
        ie problem framing, -> requirements gathering, -> vendor educations and vendor shortlist, -> commercial purchase. Do NOT include rollout
        Identify precisely who leads, who influences, and who signs off at each stage.

        Expected Output:
        In Markdown, each stage of the buyer journey and information for which role leads it, influences it, and finally signs off. Do this for each of the stages in the typical buying cycle above.
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\nMOTIVATIONS & KPIs:\n" + state.get("motivations_md", "(missing)") +
        "\n\nWATERING HOLES:\n" + state.get("watering_holes_md", "(missing)") +
        "\n\nCreate the buyer journey map. Use the web_search tool to find relevant information."
    )
    md, node_cost = run_with_tools(sys_prompt, user)
    state["total_cost"] += node_cost
    return {"buyer_journey_md": md}

def content_opportunities(state: dict) -> dict:
    """content_opportunities"""
    sys_prompt = (
        f"""
        For each role in the buying committee, keeping in mine everything we have round out about the industry, the buying committee, the buyer journey, and the watering holes, 
        translate the insights into marketing/sales plays. Specifically, identify what content resonates with each applicable roles at each stage of the cycle (technical whitepapers vs. ROI calculators vs. peer case studies, etc.)

        Expected Output:
        In Markdown, a content alignment table (role x buying stage x best content type)
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\nMOTIVATIONS & KPIs:\n" + state.get("motivations_md", "(missing)") +
        "\n\nWATERING HOLES:\n" + state.get("watering_holes_md", "(missing)") +
        "\n\nBUYER JOURNEY:\n" + state.get("buyer_journey_md", "(missing)") +
        "\n\nCreate the content opportunities. Use the web_search tool to find relevant information if you need it."
    )
    md, node_cost = run_with_tools(sys_prompt, user)
    state["total_cost"] += node_cost
    return {"content_opportunities_md": md}

def node_competitor_benchmark_report(state: dict) -> dict:
    """competitor_benchmark_report"""
    sys_prompt = (
        f"""
        In the {state.get("product_category")} segment, review how competitors bechmark their channels and messaging. Deliver a competitor messages matrix (What role they target, proof points, formats, etc.)


        Expected Output:
        In Markdown, a competitor messages matrix (What role they target, proof points, formats)
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\nMOTIVATIONS & KPIs:\n" + state.get("motivations_md", "(missing)") +
        "\n\nWATERING HOLES:\n" + state.get("watering_holes_md", "(missing)") +
        "\n\nBUYER JOURNEY:\n" + state.get("buyer_journey_md", "(missing)") +
        "\n\nCONTENT OPPORTUNITIES:\n" + state.get("content_opportunities_md", "(missing)") +
        "\n\nCreate the competitor benchmark report. Use the web_search tool to find relevant information if you need it."
    )
    md, node_cost = run_with_tools(sys_prompt, user)
    state["total_cost"] += node_cost
    return {"competitor_benchmark_report_md": md}

def node_final_review(state: dict) -> dict:
    sys = (
        f"""
        Take all the different deliverables … consolidate into one markdown document. 
        Do not leave out a single detail and do not add your own research. 
        Clearly specify the deliverables by section.
        You may change the formatting as you see fit to make it look better. Changing sections, headers, tables, to make it look good inside of a google doc is what you should do.
        Include a section for sources at the bottom of the document. You should get these sources from the other deliverables.
        Also include a introdcutory page that includes a title, the date, a short overview of the entire document/report, and then a tables of contents. Specificy the client name that we are doing this research for in the title. Client name: {state.get("client")}
        The tables of cotents should be formatted as so: 
        ## Table of Contents
        SECTION 1: Industry Scope
        SECTION 2: Stakeholder Map
        SECTION 3: Motivations & KPIs
        SECTION 4: Watering Holes
        SECTION 5: Buyer Journey
        SECTION 6: Content Opportunities
        SECTION 7: Competitor Benchmark Report
        SECTION 8: Sources"""
    )
    usr = (
        "## Industry Scope \n" + state.get("industry_scope_md", "") +
        "\n\n## Stakeholder Map …\n" + state.get("stakeholders_md", "") +
        "\n\n## Motivations & KPIs …\n" + state.get("motivations_md", "") +
        "\n\n## Watering Holes …\n" + state.get("watering_holes_md", "") +
        "\n\n## Buyer Journey …\n" + state.get("buyer_journey_md", "") +
        "\n\n## Content Opportunities …\n" + state.get("content_opportunities_md", "") +
        "\n\n## Competitor Benchmark Report …\n" + state.get("competitor_benchmark_report_md", "")
    )
    md = run_gemini_final(sys, usr)
    return {"final_review_md": md}
    


# ==============================================================
# Run test
# ==============================================================

def run_personas(state: dict):
    start_time = time.time()

    state["total_cost"] = 0.0
    state["model_used"] = model

    print('Got to run_personas')

    result = node_industry_scope(state)
    state["industry_scope_md"] = result["industry_scope_md"]
    print("Finished Industry Scope")
    
    result = node_map_stakeholders(state)
    state["stakeholders_md"] = result["stakeholders_md"]
    print("Finished Stakeholder Map")
    
    result = node_motivations_kpis(state)
    state["motivations_md"] = result["motivations_md"]
    print("Finished Motivations & KPIs")
    
    result = node_watering_holes(state)
    state["watering_holes_md"] = result["watering_holes_md"]
    print("Finished Watering Holes")
    
    result = node_buyer_journey(state)
    state["buyer_journey_md"] = result["buyer_journey_md"]
    print("Finished Buyer Journey")
    
    result = content_opportunities(state)
    state["content_opportunities_md"] = result["content_opportunities_md"]
    print("Finished Content Opportunities")

    result = node_competitor_benchmark_report(state)
    state["competitor_benchmark_report_md"] = result["competitor_benchmark_report_md"]
    print("Finished Competitor Benchmark Report")
    
    result = node_final_review(state)
    state["final_review_md"] = result["final_review_md"]
    print(state["final_review_md"])

    end_time = time.time()
    elapsed_seconds = end_time - start_time
    
    minutes, seconds = divmod(elapsed_seconds, 60)

    state["runtime_human"] = f"{minutes} minutes {seconds} seconds"

    today = datetime.date.today()
    formatted_date = today.strftime("%m/%d/%Y")

    convert_to_gdoc(state["final_review_md"], title=f"{state['client']} AI-GEN Persona Report {formatted_date}", recipient_email=state["email"], state=state)

    

