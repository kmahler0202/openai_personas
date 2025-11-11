# app.py
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Persona Generation Imports
from processes.persona_gen import run_persona_generation

# Deck Generation Imports
from processes.deck_gen.generate_deck import run_deck_generation

# RFP Launchpad Imports
from processes.rfp_launchpad.rfp_breakdown import breakdown_rfp
from processes.rfp_launchpad.rfp_answer import answer_rfp_questions, RESPONSE_MODEL, TOP_K
from processes.rfp_launchpad.identify_sme import identify_sme

from services import get_google_services, send_deck_with_attachment, send_rfp_answers_email
from services.gdrive_service import extract_pdf_text_from_drive

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
        "deck_description": payload.get("Description", ""),
        "rfp_id": payload.get("Submit RFP Here", ""),
        "new_prospect": True if payload.get("New Prospect?", "") == "Yes" else False,
        # TODO: figure out what the rest of the RFP LP fields are.
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
            # Generate the persona report
            result = run_persona_generation(form_data)
            
            # Check if generation was successful
            if not result.get("success"):
                print(f"❌ Persona generation failed: {result.get('error')}")
                return jsonify({"error": result.get("error")}), 500
                
        elif(desired_tool == "Deck Generation"):
            # Generate the deck
            result = run_deck_generation(form_data["deck_description"])
            
            # Check if deck generation was successful
            if result.get("success"):
                # Get Google services for email
                _, _, gmail_service = get_google_services()
                
                # Send email with PowerPoint attachment
                recipient_email = form_data.get("email")
                if recipient_email:
                    try:
                        send_deck_with_attachment(
                            gmail_service=gmail_service,
                            recipient_email=recipient_email,
                            pptx_path=result["pptx_path"],
                            deck_title="Mx AI Deck",
                            deck_description=form_data["deck_description"]
                        )
                        print(f"✅ Deck emailed to {recipient_email}")
                    except Exception as email_error:
                        print(f"⚠️ Deck generated but email failed: {email_error}")
                        # Don't fail the whole request if email fails
                else:
                    print("⚠️ No email provided, skipping email notification")
            else:
                print(f"❌ Deck generation failed: {result.get('error')}")
                return jsonify({"error": result.get("error")}), 500
        elif(desired_tool == "RFP LaunchPad"):

            # Get Google services for Google Drive
            _, drive_service, gmail_service = get_google_services()
            
            file_id = form_data["rfp_id"][0]
            print(f"📋 Attempting to extract PDF from Drive with file_id: {file_id}")
            
            try:
                pdf_text = extract_pdf_text_from_drive(drive_service, file_id)
                print(f"✅ PDF text extracted from Drive ({len(pdf_text)} characters)")

                # Breakdown the RFP
                breakdown = breakdown_rfp(pdf_text)
                print(f"✅ RFP breakdown complete")

                # Identify the best SME
                for question in breakdown["questions_to_answer"]:
                    sme = identify_sme(question)
                    print(f"✅ SME identified: {sme['full_name']} ({sme['role']}, {sme['department']}, {sme['email']})")
                
                # Answer the RFP questions
                result = answer_rfp_questions(breakdown["questions_to_answer"])
                answers = result["answers"]
                metadata = result["metadata"]
                print(f"✅ RFP questions answered: {len(answers)} questions")
                
                # Send email with results
                recipient_email = form_data.get("email")
                if recipient_email:
                    try:
                        # Calculate average relevance score from answers
                        relevance_scores = [ans.get('avg_relevance_score', 0) for ans in answers if ans.get('avg_relevance_score')]
                        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
                        
                        # Format runtime
                        elapsed = metadata.get("elapsed_time", 0)
                        if elapsed < 60:
                            runtime_human = f"{elapsed:.1f} seconds"
                        elif elapsed < 3600:
                            runtime_human = f"{elapsed / 60:.1f} minutes"
                        else:
                            runtime_human = f"{elapsed / 3600:.2f} hours"
                        
                        # Prepare run metadata for email
                        run_metadata = {
                            "total_questions": metadata.get("total_questions", len(answers)),
                            "total_time": elapsed,
                            "runtime_human": runtime_human,
                            "avg_relevance_score": avg_relevance,
                            "model_used": RESPONSE_MODEL,
                            "top_k": TOP_K
                        }
                        
                        # Send email
                        send_rfp_answers_email(
                            gmail_service=gmail_service,
                            recipient_email=recipient_email,
                            answers=answers,
                            run_metadata=run_metadata
                        )
                        print(f"✅ RFP answers emailed to {recipient_email}")
                    except Exception as email_error:
                        print(f"⚠️ RFP answers generated but email failed: {email_error}")
                        # Don't fail the whole request if email fails
                else:
                    print("⚠️ No email provided, skipping email notification")
            
            except Exception as e:
                print(f"❌ Error in RFP LaunchPad pipeline: {e}")
                print(f"Full traceback: {traceback.format_exc()}")
                return jsonify({"error": f"RFP LaunchPad failed: {str(e)}"}), 500
        
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
