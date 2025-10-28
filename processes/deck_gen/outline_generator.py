#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
load_dotenv()

# pip install openai>=1.0.0
from openai import OpenAI

def load_json(p: Path) -> Any:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # remove first fence line
        t = t.split("\n", 1)[1] if "\n" in t else ""
        # remove trailing ``` if present
        if t.endswith("```"):
            t = t[: -3].rstrip()
        # remove a possible leading language tag
        if t.splitlines() and t.splitlines()[0].strip().startswith("{") is False and "{" in t:
            t = t[t.index("{") :]
    return t

def generate_outline(
    *,
    model: str,
    template_map: Dict[str, Any],
    use_cases: Dict[str, Any],
    deck_meta: Dict[str, str],
    brief_text: str,
) -> Dict[str, Any]:
    """
    Minimal: push template_map + use_cases raw into system; brief/meta into user; expect strict JSON back.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    system_prompt = f"""
You are an expert slide architect. Output STRICT JSON only (no prose, no code fences).

You are given:
1) A slide template map (exact layout and placeholder names).
2) Human-made use cases mapping slide intents to layouts.

Task:
- Produce a deck outline ready for rendering by a renderer that directly maps strings into placeholders.
- For each slide, choose one layout by its exact "name" from the template map.
- For that layout, create "placeholders": an object whose keys are the EXACT placeholder names from the map.
- If a placeholder isn't needed, set it to "" (do not omit).
- Keep copy concise and on-brand. Max ~5 bullets if a bullets placeholder exists.
- If there are picture/image placeholders, set them to "" in this version.
- If bullets or a number list already exists in the template, strip it away from the plan so that it is not double included in the final deck.

Required JSON shape:
{{
  "deck_meta": {{
    "title": str,
    "author": str,
    "date": str,
    "brand": str
  }},
  "deck_slides": [
    {{
      "layout_name": str,
      "master_index": int,
      "layout_index": int,
      "placeholders": {{
        "<exact_placeholder_name_from_template_map>": str,
        "...": "..."
      }}
    }}
  ]
}}

TEMPLATE_MAP (verbatim JSON):
{json.dumps(template_map, ensure_ascii=False)}

USE_CASES (verbatim JSON):
{json.dumps(use_cases, ensure_ascii=False)}
""".strip()

    user_prompt = f"""
BRIEF (free text from user):
{brief_text.strip() if brief_text else ""}

DECK META:
{json.dumps(deck_meta, ensure_ascii=False)}

Instructions:
- Use the meta above where appropriate (e.g., title/author/date placeholders).
- Return ONLY the JSON specified. No explanations.
""".strip()

    # Minimal chat call
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content or ""
    content = strip_code_fences(content)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Fail loudly but include raw for debugging
        raise SystemExit(f"LLM did not return valid JSON: {e}\n\n--- RAW ---\n{content}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template-map", type=Path, default=Path("templates/template_map.json"))
    ap.add_argument("--use-cases", type=Path, default=Path("templates/template_use_cases.json"))
    ap.add_argument("--brief", type=Path, help="Path to a text brief for the deck")
    ap.add_argument("--title", default="Automatic Deck Generation")
    ap.add_argument("--author", default="Kyle Mahler")
    ap.add_argument("--brand", default="mx")
    ap.add_argument("--date", default="")
    ap.add_argument("--out", type=Path, default=Path("output/outline.json"))
    ap.add_argument("--model", default="gpt-5")
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY in your environment.")

    template_map = load_json(args.template_map)
    use_cases = load_json(args.use_cases)

    brief_text = ""
    if args.brief:
        brief_text = Path(args.brief).read_text(encoding="utf-8")

    deck_meta = {
        "title": args.title,
        "author": args.author,
        "date": args.date,
        "brand": args.brand,
    }

    outline = generate_outline(
        model=args.model,
        template_map=template_map,
        use_cases=use_cases,
        deck_meta=deck_meta,
        brief_text=brief_text,
    )

    save_json(args.out, outline)
    print(f"Wrote outline → {args.out}")

if __name__ == "__main__":
    main()
