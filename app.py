# app.py
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from main import run_personas

from processes.deck_gen.generate_deck import run_deck_generation

# Your modules (from earlier messages)
# from crew_runner import run_buyer_ecosystem_crew
# from google_docs import create_doc_with_content

# ---------- Bootstrap ----------
load_dotenv()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # optional locally


app = Flask(__name__)



# ---------- Helpers ----------
def _verify_secret(req) -> bool:
    """
    If WEBHOOK_SECRET is set, require X-Webhook-Secret header to match.
    If not set, allow (useful for quick local dev).
    """
    if not WEBHOOK_SECRET:
        return True
    return req.headers.get("X-Webhook-Secret", "") == WEBHOOK_SECRET


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert form payload to a standard format
    """
    form_data = {
        "product_category": payload.get("Product Category", ""),
        "target_market_segments": payload.get("Target Market Segments", ""),
        "target_geographies": payload.get("Target Geographies", ""),
        "email": payload.get("MX Email", ""),
        "client": payload.get("Client", ""),
        "tool": payload.get("Select Desired Tool", ""),
        "deck_description": payload.get("Description", "")
    }

    # Optional idempotency key if caller sends it
    form_data["submission_id"] = payload.get("submission_id") or f"sub-{int(datetime.utcnow().timestamp())}"
    return form_data


# ---------- Routes ----------
@app.get("/")
def hello_world():
    return "Hello, World!"

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/version")
def version():
    return jsonify({"version": APP_VERSION}), 200



# this is good and tested all the way up until run_buyer_ecosystem_crew
@app.post("/forms-webhook")
def forms_webhook():
    print("Got To /forms-webhook")
    try:
        if not _verify_secret(request):
            return jsonify({"error": "unauthorized"}), 401
        payload = request.get_json(force=True)
        form_data = _normalize_payload(payload)

        desired_tool = form_data.get("tool", "")

        if(desired_tool == "Buyer Ecosystem, Personas, and Content Reccomendations"):
            run_personas(form_data)
        elif(desired_tool == "Deck Generation"):
            run_deck_generation(form_data["deck_description"])

        
        return jsonify({
            "status": "success"         
        }), 200
    except Exception as e:
        app.logger.error("Webhook error: %s\n%s", e, traceback.format_exc())
        return jsonify({"error": "internal_error"}), 500


if __name__ == "__main__":
    # Local dev server; in Docker/prod we use gunicorn
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=True)
