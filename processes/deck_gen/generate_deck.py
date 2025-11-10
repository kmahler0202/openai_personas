#!/usr/bin/env python3
"""
generate_deck.py
----------------
One-call function to run the entire deck generation pipeline:
1. content_generator - Generate human-readable plan from brief
2. outline_generator - Generate structured JSON outline
3. outline_to_ppt - Render final PowerPoint presentation

Usage:
  python src/generate_deck.py --brief "Create a product launch deck..." --out output/my_deck.pptx
  
  python src/generate_deck.py --brief briefs/project_brief.txt --title "Q4 Strategy" --author "John Doe"
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Import the core functions from each module
from .content_generator import generate_plan, load_json, load_use_cases
from .outline_generator import generate_outline, save_json
from .outline_to_ppt import render

load_dotenv()

ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = ROOT / "templates" / "mx_powerpoint_template_v3.pptx"
DEFAULT_TEMPLATE_MAP = ROOT / "templates" / "template_map.json"
DEFAULT_USE_CASES = ROOT / "templates" / "template_use_cases.json"
DEFAULT_OUTPUT_DIR = ROOT / "output"


def generate_deck_pipeline(
    *,
    brief: str,
    template_pptx: Path,
    template_map: Path,
    use_cases: Path,
    output_dir: Path,
    deck_title: str,
    author: str,
    brand: str,
    date: str,
    model: str = "gpt-5",
    skip_plan: bool = False,
    verbose: bool = True,
) -> Path:
    """
    Run the complete deck generation pipeline.
    
    Args:
        brief: Project brief text (or path will be read if exists)
        template_pptx: Path to PowerPoint template file
        template_map: Path to template_map.json
        use_cases: Path to template_use_cases.json
        output_dir: Directory for all output files
        deck_title: Title for the deck
        author: Author name
        brand: Brand identifier
        date: Date string (defaults to today if empty)
        model: OpenAI model to use (default: gpt-5)
        skip_plan: Skip content plan generation step (default: False)
        verbose: Print progress messages (default: True)
    
    Returns:
        Path to the generated PowerPoint file
    """
    print('Got to generate_deck_pipeline')
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set default date if not provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Read brief from file if it exists
    brief_text = brief
    if Path(brief).exists():
        brief_text = Path(brief).read_text(encoding="utf-8")
        if verbose:
            print(f"📄 Loaded brief from: {brief}")
    
    # Define output paths
    plan_path = output_dir / f"plan_{timestamp}.txt"
    outline_path = output_dir / f"outline_{timestamp}.json"
    final_pptx = output_dir / f"deck_{timestamp}.pptx"
    
    # ========================================
    # STEP 1: Generate Content Plan (Optional)
    # ========================================
    if not skip_plan:
        if verbose:
            print("\n" + "="*60)
            print("STEP 1/3: Generating content plan...")
            print("="*60)
        
        use_cases_data = load_use_cases(use_cases)
        template_map_data = load_json(template_map)
        
        plan = generate_plan(
            brief=brief_text,
            use_cases=use_cases_data,
            template_map=template_map_data,
            model=model
        )
        
        plan_path.write_text(plan, encoding="utf-8")
        if verbose:
            print(f"✅ Content plan saved to: {plan_path}")
            print(f"\n{plan}\n")
    else:
        if verbose:
            print("\n⏭️  Skipping content plan generation")
    
    # ========================================
    # STEP 2: Generate Structured Outline
    # ========================================
    if verbose:
        print("\n" + "="*60)
        print("STEP 2/3: Generating structured outline...")
        print("="*60)
    
    template_map_data = load_json(template_map)
    use_cases_data = load_json(use_cases)
    
    deck_meta = {
        "title": deck_title,
        "author": author,
        "date": date,
        "brand": brand,
    }
    
    outline = generate_outline(
        model=model,
        template_map=template_map_data,
        use_cases=use_cases_data,
        deck_meta=deck_meta,
        brief_text=plan,
    )
    
    save_json(outline_path, outline)
    if verbose:
        print(f"✅ Outline saved to: {outline_path}")
        print(f"   Slides generated: {len(outline.get('deck_slides', []))}")
    
    # ========================================
    # STEP 3: Render PowerPoint
    # ========================================
    if verbose:
        print("\n" + "="*60)
        print("STEP 3/3: Rendering PowerPoint presentation...")
        print("="*60)
    
    render(
        template_pptx=template_pptx,
        template_map_path=template_map,
        outline_path=outline_path,
        out_path=final_pptx,
    )
    
    if verbose:
        print(f"✅ PowerPoint saved to: {final_pptx}")
        print("\n" + "="*60)
        print("🎉 PIPELINE COMPLETE!")
        print("="*60)
        print(f"\n📊 Final deck: {final_pptx}")
        print(f"📝 Outline: {outline_path}")
        if not skip_plan:
            print(f"📄 Plan: {plan_path}")
    
    return final_pptx


def main():
    ap = argparse.ArgumentParser(
        description="Run the complete deck generation pipeline in one call",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with brief text
  python src/generate_deck.py --brief "Create a product launch deck for our new AI assistant"
  
  # Use a brief file
  python src/generate_deck.py --brief briefs/q4_strategy.txt --title "Q4 Strategy Review"
  
  # Customize author and brand
  python src/generate_deck.py --brief "Sales enablement deck" --author "Jane Smith" --brand "acme"
  
  # Skip the content plan step
  python src/generate_deck.py --brief "Quick update deck" --skip-plan
        """
    )
    
    # Required arguments
    ap.add_argument(
        "--brief",
        type=str,
        required=True,
        help="Project brief text or path to .txt file containing the brief"
    )
    
    # Output arguments
    ap.add_argument(
        "--out",
        type=Path,
        help="Path for final PowerPoint file (default: output/deck_TIMESTAMP.pptx)"
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for all output files (default: output/)"
    )
    
    # Deck metadata
    ap.add_argument(
        "--title",
        type=str,
        default="Automatic Deck Generation",
        help="Deck title (default: 'Automatic Deck Generation')"
    )
    ap.add_argument(
        "--author",
        type=str,
        default="Kyle Mahler",
        help="Author name (default: 'Kyle Mahler')"
    )
    ap.add_argument(
        "--brand",
        type=str,
        default="mx",
        help="Brand identifier (default: 'mx')"
    )
    ap.add_argument(
        "--date",
        type=str,
        default="",
        help="Date string (default: today's date)"
    )
    
    # Template arguments
    ap.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Path to PowerPoint template file"
    )
    ap.add_argument(
        "--template-map",
        type=Path,
        default=DEFAULT_TEMPLATE_MAP,
        help="Path to template_map.json"
    )
    ap.add_argument(
        "--use-cases",
        type=Path,
        default=DEFAULT_USE_CASES,
        help="Path to template_use_cases.json"
    )
    
    # Model and behavior
    ap.add_argument(
        "--model",
        type=str,
        default="gpt-5",
        help="OpenAI model to use (default: 'gpt-5')"
    )
    ap.add_argument(
        "--skip-plan",
        action="store_true",
        help="Skip content plan generation step"
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )
    
    args = ap.parse_args()
    
    # Validate API key
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("❌ Error: OPENAI_API_KEY not found in environment. Set it in .env file.")
    
    # Validate template files exist
    if not args.template.exists():
        raise SystemExit(f"❌ Error: Template file not found: {args.template}")
    if not args.template_map.exists():
        raise SystemExit(f"❌ Error: Template map not found: {args.template_map}")
    if not args.use_cases.exists():
        raise SystemExit(f"❌ Error: Use cases file not found: {args.use_cases}")
    
    # Run the pipeline
    final_pptx = generate_deck_pipeline(
        brief=args.brief,
        template_pptx=args.template,
        template_map=args.template_map,
        use_cases=args.use_cases,
        output_dir=args.output_dir,
        deck_title=args.title,
        author=args.author,
        brand=args.brand,
        date=args.date,
        model=args.model,
        skip_plan=args.skip_plan,
        verbose=not args.quiet,
    )
    
    # If custom output path specified, rename the final file
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        final_pptx.rename(args.out)
        if not args.quiet:
            print(f"\n📦 Moved to custom location: {args.out}")

def run_deck_generation(deck_description: str) -> Dict[str, Any]:
    """
    Run deck generation pipeline from Flask app.
    
    This function is designed to be called from a Flask route handler.
    It accepts a deck description string and runs the complete pipeline with default settings.
    
    Args:
        deck_description (str): The project brief text describing the deck to generate
    
    Returns:
        Dictionary containing:
            - success (bool): Whether the pipeline succeeded
            - pptx_path (str): Path to generated PowerPoint file (if successful)
            - outline_path (str): Path to outline JSON file (if successful)
            - plan_path (str): Path to content plan file (if successful)
            - error (str): Error message (if failed)
    """
    print("Got to run_deck_generation")
    try:
        # Validate input
        if not deck_description:
            return {
                "success": False,
                "error": "Deck description is required"
            }
        
        # Set defaults for all parameters
        deck_title = "Dogs - The Future of MX"
        author = "Kyle Mahler"
        brand = "MX"
        date = datetime.now().strftime("%Y-%m-%d")
        model = "gpt-5"
        skip_plan = False
        
        # Set default paths
        template_pptx = DEFAULT_TEMPLATE
        template_map = DEFAULT_TEMPLATE_MAP
        use_cases = DEFAULT_USE_CASES
        output_dir = DEFAULT_OUTPUT_DIR
        
        # Validate template files exist
        if not template_pptx.exists():
            print(f"Template file not found: {template_pptx}")
            return {
                "success": False,
                "error": f"Template file not found: {template_pptx}"
            }
        if not template_map.exists():
            print(f"Template map file not found: {template_map}")
            return {
                "success": False,
                "error": f"Template map file not found: {template_map}"
            }
        if not use_cases.exists():
            print(f"Use cases file not found: {use_cases}")
            return {
                "success": False,
                "error": f"Use cases file not found: {use_cases}"
            }
        
        # Run the pipeline with verbose=False for Flask (no console output)
        pptx_path = generate_deck_pipeline(
            brief=deck_description,
            template_pptx=template_pptx,
            template_map=template_map,
            use_cases=use_cases,
            output_dir=output_dir,
            deck_title=deck_title,
            author=author,
            brand=brand,
            date=date,
            model=model,
            skip_plan=skip_plan,
            verbose=True
        )
        
        # Generate the other paths for reference
        timestamp = pptx_path.stem.replace("deck_", "")
        outline_path = output_dir / f"outline_{timestamp}.json"
        plan_path = output_dir / f"plan_{timestamp}.txt"
        
        result = {
            "success": True,
            "pptx_path": str(pptx_path),
            "outline_path": str(outline_path),
        }
        
        if not skip_plan and plan_path.exists():
            result["plan_path"] = str(plan_path)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    main()
