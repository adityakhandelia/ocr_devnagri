"""End-to-end NER pipeline: OCR text → indexed wordlist → LLM → entity JSON."""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.ner_indexer import index_ocr_page_for_ner
from scripts.ner_llm_parser import (
    build_ner_prompt,
    call_llm,
    extract_json_from_response,
    parse_with_retry,
    validate_ner_output,
)

OCR_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2")
EXAMPLES_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/ner_examples")
OUTPUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/ner_parsed")
FINAL_JSON = Path("C:/Users/adity/Desktop/ocr_devnagri/data/ner_parsed/all_entities.json")

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


def parse_page(txt_path: Path, model: Optional[str] = None) -> dict:
    """Parse a single OCR page through the NER LLM."""
    page_data = index_ocr_page_for_ner(txt_path)

    print(
        f"NER for page {page_data['page_number']} "
        f"({page_data['total_words']} words) with model {model or DEFAULT_MODEL}..."
    )
    llm_output = parse_with_retry(page_data["words"], EXAMPLES_DIR, model=model)

    return {
        "page_number": page_data["page_number"],
        "total_words": page_data["total_words"],
        "entities": llm_output.get("entities", []),
    }


def parse_all_pages(limit: Optional[int] = None, model: Optional[str] = None):
    """Parse all OCR pages and save per-page NER output."""
    if not any(EXAMPLES_DIR.glob("*_input.txt")):
        print("Warning: No NER examples found in scripts/ner_examples/.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(OCR_DIR.glob("*.txt"))
    if limit:
        txt_files = txt_files[:limit]

    all_pages = []

    for txt_path in txt_files:
        if ".error" in txt_path.name:
            continue

        result = parse_page(txt_path, model=model)

        out_path = OUTPUT_DIR / f"page_{result['page_number']:03d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        all_pages.append(
            {
                "page_number": result["page_number"],
                "total_words": result["total_words"],
                "entity_count": len(result["entities"]),
            }
        )

    FINAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FINAL_JSON, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Parsed {len(all_pages)} pages.")
    print(f"Saved per-page JSONs to {OUTPUT_DIR}")
    print(f"Saved summary to {FINAL_JSON}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run NER parsing on OCR pages")
    parser.add_argument("--limit", type=int, default=None, help="Only parse first N pages")
    parser.add_argument("--page", type=int, default=None, help="Parse a single page number")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="LLM model via OpenRouter",
    )
    parser.add_argument(
        "--prompt-only",
        type=int,
        default=None,
        help="Generate prompt for a page and save it without calling the API",
    )
    args = parser.parse_args()

    if args.prompt_only:
        txt_path = OCR_DIR / f"1952_1_100_2_page_{args.prompt_only:03d}.txt"
        if not txt_path.exists():
            txt_path = OCR_DIR / f"page_{args.prompt_only:03d}.txt"
        page_data = index_ocr_page_for_ner(txt_path)
        prompt = build_ner_prompt(page_data["words"], EXAMPLES_DIR)
        out_path = Path(f"scripts/ner_prompt_page_{args.prompt_only:03d}.txt")
        out_path.write_text(prompt, encoding="utf-8")
        print(f"Prompt saved to {out_path} ({len(prompt):,} characters)")
    elif args.page:
        txt_path = OCR_DIR / f"1952_1_100_2_page_{args.page:03d}.txt"
        if not txt_path.exists():
            txt_path = OCR_DIR / f"page_{args.page:03d}.txt"
        result = parse_page(txt_path, model=args.model)
        out_path = OUTPUT_DIR / f"page_{result['page_number']:03d}.json"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Saved page {result['page_number']} result to {out_path}")
    else:
        parse_all_pages(limit=args.limit, model=args.model)
