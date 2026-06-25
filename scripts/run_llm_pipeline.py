"""End-to-end pipeline: OCR text → LLM → structured JSON for UI."""
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.index_ocr_page import index_ocr_file, format_wordlist, _extract_page_number
from scripts.llm_parser import (
    parse_with_retry,
    reconstruct_segments,
)

# Configuration
OCR_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2")
EXAMPLES_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/llm_examples")
OUTPUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/llm_parsed")
OUTPUT_DIR_CLEAN = Path("C:/Users/adity/Desktop/ocr_devnagri/data/llm_parsed_clean")
FINAL_JSON = Path("C:/Users/adity/Desktop/ocr_devnagri/frontend/public/data/debates_llm.json")

SESSION_DATE = "1952-03-07"
SESSION_TITLE = "उत्तर प्रदेश विधान सभा - 7 मार्च 1952"
PDF_NAME = "1952_1_100_2.pdf"


def clean_page_segments(segments: List[dict]) -> List[dict]:
    """Ensure every segment has required fields and clean text."""
    for seg in segments:
        seg.setdefault("subtype", None)
        seg.setdefault("speaker", None)
    return segments


def compute_page_stats(segments: List[dict]) -> dict:
    """Compute per-page segment statistics."""
    stats = {}
    for seg in segments:
        key = seg["type"]
        stats[key] = stats.get(key, 0) + 1
    return stats


def detect_page_type(segments: List[dict]) -> str:
    """Classify page based on dominant segment types."""
    counts = {}
    for seg in segments:
        counts[seg["type"]] = counts.get(seg["type"], 0) + 1

    if counts.get("member_list", 0) > 0:
        return "member_list"
    if counts.get("speech", 0) >= 1:
        return "debate"
    if counts.get("heading", 0) > counts.get("speech", 0):
        return "proceedings"
    return "mixed"


def parse_page(txt_path: Path, model: Optional[str] = None) -> dict:
    """Parse a single OCR page through the LLM."""
    page_data = index_ocr_file(txt_path)

    print(f"Parsing page {page_data['page_number']} ({page_data['total_words']} words) with model {model or 'default'}...")
    llm_output = parse_with_retry(page_data["words"], EXAMPLES_DIR, model=model, max_retries=2)
    segments = reconstruct_segments(page_data["words"], llm_output)
    segments = clean_page_segments(segments)

    return {
        "page_number": page_data["page_number"],
        "image": f"data/full_pdf_images/1952_1_100_2/{txt_path.stem.replace('.txt', '.png')}",
        "thumbnail": f"data/full_pdf_images/1952_1_100_2/{txt_path.stem.replace('.txt', '.png')}",
        "segments": segments,
        "segment_stats": compute_page_stats(segments),
        "page_type": detect_page_type(segments),
        "total_words": page_data["total_words"],
        "llm_output": llm_output,
    }


def aggregate_existing_pages(source_dir: Optional[Path] = None) -> dict:
    """Build final JSON from parsed page files without calling the API.

    Uses the post-processed clean directory by default if it exists.
    """
    source_dir = source_dir or (OUTPUT_DIR_CLEAN if OUTPUT_DIR_CLEAN.exists() else OUTPUT_DIR)
    pages = []
    all_speakers = set()
    all_segment_stats = {}

    for page_file in sorted(source_dir.glob("page_*.json")):
        with open(page_file, "r", encoding="utf-8") as f:
            result = json.load(f)

        for seg in result["segments"]:
            if seg.get("speaker"):
                all_speakers.add(seg["speaker"])

        page_stats = result.get("segment_stats", compute_page_stats(result["segments"]))
        for key, val in page_stats.items():
            all_segment_stats[key] = all_segment_stats.get(key, 0) + val

        pages.append({
            "page_number": result["page_number"],
            "image": result.get("image", ""),
            "thumbnail": result.get("thumbnail", ""),
            "page_type": result.get("page_type", "mixed"),
            "total_words": result.get("total_words", 0),
            "segment_stats": page_stats,
            "segments": result["segments"],
        })

    debate_data = {
        "pdf_name": PDF_NAME,
        "date": SESSION_DATE,
        "session_title": SESSION_TITLE,
        "total_pages": len(pages),
        "total_words": sum(p.get("total_words", 0) for p in pages),
        "speakers": sorted(list(all_speakers)),
        "segment_counts": all_segment_stats,
        "pages": pages,
    }

    FINAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FINAL_JSON, "w", encoding="utf-8") as f:
        json.dump(debate_data, f, ensure_ascii=False, indent=2)

    print(f"Aggregated {len(pages)} pages into {FINAL_JSON}")
    return debate_data


def parse_all_pages(limit: int = None, start: int = None, model: Optional[str] = None, continue_on_error: bool = False):
    """Parse all OCR pages and save structured output."""
    if not any(EXAMPLES_DIR.glob("*_input.txt")):
        print("Warning: No examples found in scripts/llm_examples/. Add at least one example.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(OCR_DIR.glob("*.txt"))
    if start:
        txt_files = [f for f in txt_files if _extract_page_number(f) >= start]
    if limit:
        txt_files = txt_files[:limit]

    pages = []
    all_speakers = set()
    all_segment_stats = {}

    for txt_path in txt_files:
        if ".error" in txt_path.name:
            continue

        try:
            result = parse_page(txt_path, model=model)
        except Exception as e:
            print(f"  ERROR parsing page {txt_path.name}: {e}")
            if continue_on_error:
                continue
            raise

        # Save individual page JSON
        out_path = OUTPUT_DIR / f"page_{result['page_number']:03d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Collect speakers and stats
        for seg in result["segments"]:
            if seg.get("speaker"):
                all_speakers.add(seg["speaker"])
        for key, val in result["segment_stats"].items():
            all_segment_stats[key] = all_segment_stats.get(key, 0) + val

        pages.append({
            "page_number": result["page_number"],
            "image": result["image"],
            "thumbnail": result["thumbnail"],
            "page_type": result["page_type"],
            "total_words": result["total_words"],
            "segment_stats": result["segment_stats"],
            "segments": result["segments"],
        })

    # Build final debate data
    debate_data = {
        "pdf_name": PDF_NAME,
        "date": SESSION_DATE,
        "session_title": SESSION_TITLE,
        "total_pages": len(pages),
        "total_words": sum(p.get("total_words", 0) for p in pages),
        "speakers": sorted(list(all_speakers)),
        "segment_counts": all_segment_stats,
        "pages": pages,
    }

    FINAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FINAL_JSON, "w", encoding="utf-8") as f:
        json.dump(debate_data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Parsed {len(pages)} pages.")
    print(f"Saved final JSON to {FINAL_JSON}")
    print(f"Saved per-page JSONs to {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse OCR pages with LLM")
    parser.add_argument("--limit", type=int, default=None, help="Only parse first N pages")
    parser.add_argument("--start", type=int, default=None, help="Start parsing from this page number")
    parser.add_argument("--page", type=int, default=None, help="Parse a single page number")
    parser.add_argument("--model", type=str, default=None, help="LLM model via OpenRouter (default: deepseek/deepseek-v4-flash)")
    parser.add_argument("--continue-on-error", action="store_true", help="Skip failed pages instead of stopping")
    parser.add_argument("--aggregate", action="store_true", help="Build final JSON from existing per-page files without API calls")
    args = parser.parse_args()

    if args.aggregate:
        aggregate_existing_pages()
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
        parse_all_pages(limit=args.limit, start=args.start, model=args.model, continue_on_error=args.continue_on_error)
