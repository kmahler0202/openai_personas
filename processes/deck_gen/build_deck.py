# src/build_deck.py
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any, Dict, List

from pptx import Presentation  # only for a fast template sanity check

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "templates" / "mx_template_powerpoint_v2.pptx"
DEFAULT_TMAP = ROOT / "templates" / "template_map.json"
DEFAULT_OUT = ROOT / "output" / "deck_autogen.pptx"

# Constraints (match outline_generator schema)
MAX_TITLE_LEN = 80
MAX_BULLETS = 5
MAX_BULLET_LEN = 140

# ---- helpers ----
def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def _validate_outline(deck: Dict[str, Any]):
    if "deck_slides" not in deck or not isinstance(deck["deck_slides"], list) or not deck["deck_slides"]:
        raise ValueError("Outline must contain a non-empty 'deck_slides' array.")
    for i, s in enumerate(deck["deck_slides"]):
        st = s.get("slide_type")
        if not isinstance(st, str):
            raise ValueError(f"Slide {i}: missing or invalid 'slide_type'.")
        if "title" in s and (not isinstance(s["title"], str) or len(s["title"]) > MAX_TITLE_LEN):
            raise ValueError(f"Slide {i}: 'title' too long or invalid.")
        if "bullets" in s:
            b = s["bullets"]
            if not isinstance(b, list) or not b or len(b) > MAX_BULLETS:
                raise ValueError(f"Slide {i}: bullets must be 1–{MAX_BULLETS}.")
            for j, it in enumerate(b):
                if not isinstance(it, str) or not it.strip():
                    raise ValueError(f"Slide {i}: bullet {j} invalid.")
                if len(it) > MAX_BULLET_LEN:
                    raise ValueError(f"Slide {i}: bullet {j} too long (> {MAX_BULLET_LEN}).")
        # minimal requireds per type
        if st == "title_slide" and "title" not in s:
            raise ValueError(f"Slide {i}: 'title_slide' requires 'title'.")
        if st == "title_bullets" and (("title" not in s) or ("bullets" not in s)):
            raise ValueError(f"Slide {i}: 'title_bullets' requires 'title' and 'bullets'.")
        if st in {"image_right_content_left", "image_left_content_right"}:
            if "title" not in s or "bullets" not in s or "image" not in s:
                raise ValueError(f"Slide {i}: image+content slide requires 'title', 'bullets', and 'image'.")

def _resolve_layout_key(aliases: Dict[str, str], slide_type: str) -> str:
    lk = aliases.get(slide_type)
    if not lk:
        raise KeyError(f"No alias mapping for slide_type '{slide_type}'. Add it under 'aliases' in template_map.json.")
    return lk

def _to_slide_specs(deck: Dict[str, Any], tmap: Dict[str, Any]) -> List[Dict[str, Any]]:
    aliases = tmap.get("aliases", {})
    specs = []
    for s in deck["deck_slides"]:
        lk = _resolve_layout_key(aliases, s["slide_type"])
        content = {
            "title": s.get("title"),
            "subtitle": s.get("subtitle"),
            "bullets": s.get("bullets"),
            "body": s.get("body"),
            "image": s.get("image"),
            "notes": s.get("notes"),
        }
        # prune Nones to keep it clean
        content = {k:v for k,v in content.items() if v is not None}
        specs.append({"layout_key": lk, "content": content})
    return specs

def main():
    ap = argparse.ArgumentParser(description="Outline JSON → on-brand PPTX (role-based map)")
    ap.add_argument("--outline", type=str, help="Path to outline JSON; if omitted, read stdin")
    ap.add_argument("--template", type=str, default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--map", type=str, default=str(DEFAULT_TMAP))
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    args = ap.parse_args()

    # Load outline
    if args.outline:
        outline = _load_json(Path(args.outline))
    else:
        if sys.stdin.isatty():
            print("Provide outline via --outline or pipe JSON to stdin.", file=sys.stderr)
            sys.exit(2)
        outline = json.loads(sys.stdin.read())

    # Load map
    tmap = _load_json(Path(args.map))

    # Validate
    _validate_outline(outline)

    # Translate to slide_specs
    slide_specs = _to_slide_specs(outline, tmap)

    # Render
    from renderer_v2 import render_slides  # local import to avoid circulars
    out_path = Path(args.out)
    render_slides(Path(args.template), tmap, slide_specs, out_path)
    print(str(out_path))

if __name__ == "__main__":
    main()
