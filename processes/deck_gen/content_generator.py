# src/content_generator.py
"""
Take a user brief and the template_use_cases.json,
and generate a human-readable slide plan.

Usage:
  python src/content_generator.py --brief "We need a kickoff deck..." --out output/plan.txt
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USE_CASES = ROOT / "templates" / "template_use_cases.json"
DEFAULT_OUT = ROOT / "output" / "plan.txt"
DEFAULT_TEMPLATE_MAP = ROOT / "templates" / "template_map.json"

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def load_use_cases(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def generate_plan(brief: str, use_cases: dict, template_map: dict, model: str = "gpt-5") -> str:
    client = OpenAI()

    system_msg = (
        "You are a senior presentation strategist. "
        "Given the use cases for each template layout, "
        "you will generate a HUMAN-READABLE plan (not JSON) for a slide deck. "
        "Describe each slide in order, recommend which layout to use"
        "Also given the template map, you will make your content reccomendations based on the placeholders that hold text."
        "Do not output JSON. Do not output code. "
        "Feel free to add as much information as you see fit if the brief is vague"
        "If a layout is marked in its use cases with a DO NOT USE, then do not pick that layout."
    )

    ref_msg = "Here are the layout use cases:\n" + json.dumps(use_cases, indent=2)

    template_msg = "Here is the template map:\n" + json.dumps(template_map, indent=2)

    user_msg = "Here is the project brief:\n" + brief.strip()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "system", "content": ref_msg},
            {"role": "system", "content": template_msg},
            {"role": "user", "content": user_msg},
        ],
    )

    return resp.choices[0].message.content.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", type=str, help="Brief text or path to .txt file", required=True)
    ap.add_argument("--use-cases", type=str, default=str(DEFAULT_USE_CASES))
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--model", type=str, default="gpt-5")
    ap.add_argument("--template-map", type=str, default=str(DEFAULT_TEMPLATE_MAP))
    args = ap.parse_args()

    brief_input = args.brief
    if Path(brief_input).exists():
        brief = Path(brief_input).read_text(encoding="utf-8")
    else:
        brief = brief_input

    use_cases = load_use_cases(Path(args.use_cases))
    template_map = load_json(Path(args.template_map))
    plan = generate_plan(brief, use_cases, template_map, model=args.model)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(plan, encoding="utf-8")
    print(f"Wrote plan to {out_path}")

if __name__ == "__main__":
    main()
