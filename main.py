from __future__ import annotations
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

from md_2_gdoc import full_pipeline as convert_to_gdoc

# ==============================================================
# GPT-5 + Native Web Search Test
# ==============================================================

client = OpenAI()

def run_with_tools(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a message to GPT-5 with native web_search tool access.
    Returns the model's textual reply.
    """
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "web_search"}],
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
    )
    return response.output_text


# ==============================================================
# Example Node (Industry Scope)
# ==============================================================

def node_industry_scope(state: dict) -> dict:
    """industry_scoper"""

    sys_prompt = f"""
    Map out the structure of the Automotive dealerships industry in the United States,
    including the size of the industry as well as major ownership structures.
    This should include both new and used market segments.

    Expected Output:
    1–2 page brief on the industry context, including regulatory issues and the
    top 3–5 challenges influencing the purchase of dealership software for running the dealership as well as for
    merchandising both new and used cars.
    """

    user_prompt = (
        "Create the brief now. Use the web_search tool to find relevant and current information. Generate an output in markdown"
    )

    md = run_with_tools(sys_prompt, user_prompt)
    return {"industry_scope_md": md}


def node_map_stakeholders(state: dict) -> dict:
    """stake_holder_mapper"""
    sys_prompt = (
        f"""
        Understanding the industry scoping information, identify the most common decision makers and decision influencers in the purchase of a used car valuation and market intelligence software.
        Map their role, typical titles, and where they fit in the process (economic buyer, technical specifier, user, compliance gatekeeper, etc.).

        Expected Output:
        Role Matrix(Titles, responsibilites, decision power, involvement stage) of the core buying committee as well as those contributing to it.
        """
    )
    user = (
        "INDUSTRY SCOPE BRIEF (Markdown below):\n\n"
        f"{state.get('industry_scope_md')}\n\n"
        "Produce buying committee as specified. Use the web_search tool to find relevant information."
    )
    md = run_with_tools(sys_prompt, user)
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
    md = run_with_tools(sys_prompt, user)
    return {"motivations_md": md}

def node_watering_holes(state: dict) -> dict:
    """information_source_analyst"""
    sys_prompt = (
        f"""
        For each role defined in the buying committee, research where each stakeholder goes for insight: media, analyst firms, standards bodies, trade associations, events, and digital channels.
        Deliver a channel mapper per role (preferred trade pubs, conferences, online forums, social media platforms, newsletters, associations).

        Expected Output:
        In Markdown, a table of channels for each role.
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\nMOTIVATIONS & KPIs:\n" + state.get("motivations_md", "(missing)") +
        "\n\nCreate the channel map. Use the web_search tool to find relevant information."
    )
    md = run_with_tools(sys_prompt, user)
    return {"watering_holes_md": md}

def node_buyer_journey(state: dict) -> dict:
    """buying_journey_analyst"""
    sys_prompt = (
        f"""
        For the core buying unit and for other defined decision influencers, outline how these roles interact through the typical buying cycle,
        ie problem farming, -> requirements gathering, -> vendor educations and vendor shortlist, -> commercial purchase, -> rollout.
        Identify precisely who leads, who influences, and who signs off at each stage.

        Expected Output:
        In Markdown, a table of the buyer journey map (roles x stages of influence)
        """
    )
    user = (
        "INDUSTRY SCOPE:\n" + state.get("industry_scope_md", "(missing)") +
        "\n\nBUYING COMMITTEE:\n" + state.get("stakeholders_md", "(missing)") +
        "\n\nMOTIVATIONS & KPIs:\n" + state.get("motivations_md", "(missing)") +
        "\n\nWATERING HOLES:\n" + state.get("watering_holes_md", "(missing)") +
        "\n\nCreate the buyer journey map. Use the web_search tool to find relevant information."
    )
    md = run_with_tools(sys_prompt, user)
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
    md = run_with_tools(sys_prompt, user)
    return {"content_opportunities_md": md}


def node_final_review(state: dict) -> dict:
    """project_manager"""
    sys_prompt = (
        f"""Take all of the different deliverables from the buyer ecosystem and content strategy research done before 
        you and simply consolidate it all into one markdown document. Use your context and just make it one big markdown document.
        Do not leave out a single detail and do not add your own research. 
        Clearly specifiy the deliverables by section """
    )
    user = (
        "## Industry Scope (Agent: industry_scoper)\n" + state.get("industry_scope_md", "(missing)") +
        "\n\n## Stakeholder Map (Agent: stake_holder_mapper)\n" + state.get("stakeholders_md", "(missing)") +
        "\n\n## Motivations & KPIs (Agent: motivator_and_kpi_analyst)\n" + state.get("motivations_md", "(missing)") +
        "\n\n## Watering Holes (Agent: information_source_analyst)\n" + state.get("watering_holes_md", "(missing)") +
        "\n\n## Buyer Journey (Agent: buying_journey_analyst)\n" + state.get("buyer_journey_md", "(missing)") +
        "\n\n## Content Opportunities (Agent: content_opportunities)\n" + state.get("content_opportunities_md", "(missing)")
    )
    md = run_with_tools(sys_prompt, user)
    return {"final_review_md": md}


# ==============================================================
# Run test
# ==============================================================

def run_personas():

    print('Got to run_personas')

    state = {
        "customer_industry": "Automotive dealership Structures",
        "client_product": "dealership software for running the delarship as well as for merchandising both new and used cars"
    }

    result = node_industry_scope({})
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
    
    result = node_final_review(state)
    state["final_review_md"] = result["final_review_md"]
    print(state["final_review_md"])

    convert_to_gdoc(state["final_review_md"], title="FULL PIPELINE ALL DELIVERABLES")




if __name__ == "__main__":

    state = {
        "customer_industry": "Automotive dealership Structures",
        "client_product": "dealership software for running the delarship as well as for merchandising both new and used cars"
    }


    # result = node_industry_scope({})
    # state["industry_scope_md"] = result["industry_scope_md"]
    # print("Finished Industry Scope")
    
    # result = node_map_stakeholders(state)
    # state["stakeholders_md"] = result["stakeholders_md"]
    # print("Finished Stakeholder Map")
    
    # result = node_motivations_kpis(state)
    # state["motivations_md"] = result["motivations_md"]
    # print("Finished Motivations & KPIs")
    
    # result = node_watering_holes(state)
    # state["watering_holes_md"] = result["watering_holes_md"]
    # print("Finished Watering Holes")
    
    # result = node_buyer_journey(state)
    # state["buyer_journey_md"] = result["buyer_journey_md"]
    # print("Finished Buyer Journey")
    
    # result = content_opportunities(state)
    # state["content_opportunities_md"] = result["content_opportunities_md"]
    # print("Finished Content Opportunities")
    
    # result = node_final_review(state)
    # state["final_review_md"] = result["final_review_md"]
    # print(state["final_review_md"])

    # convert_to_gdoc(state["final_review_md"], title="OPENAI SDK PERSONA 10/6/25 MD2GDOC", render_images=False)
    convert_to_gdoc('Test Test Test append this to gdoc', title="OPENAI SDK PERSONA 10/6/25 MD2GDOC")

