"""Full pipeline: PDF -> Images -> OCR -> JSON for frontend."""
import json
import os
import sys
from pathlib import Path

import fitz
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.pipeline_tracker import (
    init_pipeline_db,
    mark_page_done,
    mark_page_failed,
    get_pdf_progress,
    upsert_page,
)
from src.utils.ocr_engine import get_gemini_ocr
from scripts.parse_debates import parse_pdf_debates

load_dotenv()

# Configuration
PDF_NAME = "1952_1_100_2.pdf"
PDF_STEM = PDF_NAME.replace('.pdf', '')
PDF_PATH = Path(f"C:/Users/adity/Desktop/ocr_devnagri/ceDscX/{PDF_NAME}")
IMAGES_DIR = Path(f"C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_images/{PDF_STEM}")
OCR_DIR = Path(f"C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/{PDF_STEM}")
PIPELINE_DB = Path("C:/Users/adity/Desktop/ocr_devnagri/data/pipeline.db")
OUTPUT_JSON = Path("C:/Users/adity/Desktop/ocr_devnagri/frontend/public/data/debates.json")

SESSION_DATE = "1952-03-07"
SESSION_TITLE = "उत्तर प्रदेश विधान सभा - 7 मार्च 1952"


def convert_pdf_to_images():
    """Convert all PDF pages to 300 DPI PNG images."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    init_pipeline_db(PIPELINE_DB)

    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)

    print(f"Converting {total_pages} pages to images...")

    for page_num in range(total_pages):
        page_index = page_num + 1
        output_path = IMAGES_DIR / f"{PDF_STEM}_page_{page_index:03d}.png"
        ocr_path = OCR_DIR / f"{PDF_STEM}_page_{page_index:03d}.txt"

        # Register/update page record in tracker
        upsert_page(
            pdf_name=PDF_NAME,
            pdf_path=str(PDF_PATH),
            page_number=page_index,
            image_path=str(output_path),
            ocr_text_path=str(ocr_path),
            ocr_status="pending" if not ocr_path.exists() else "done",
            db_path=PIPELINE_DB,
        )

        if output_path.exists():
            print(f"  Page {page_index}/{total_pages} already exists, skipping")
            continue

        page = doc[page_num]
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(output_path))
        print(f"  Saved page {page_index}/{total_pages}")

    doc.close()
    print("PDF conversion complete.\n")


def run_ocr():
    """Run OCR on all page images."""
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    init_pipeline_db(PIPELINE_DB)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    image_files = sorted(IMAGES_DIR.glob(f"{PDF_STEM}_page_*.png"))
    total = len(image_files)

    # Estimate cost from tracker progress
    progress = get_pdf_progress(PDF_NAME, PIPELINE_DB)
    remaining = progress["pending"] + progress["failed"]

    print(f"Running OCR on {total} pages ({remaining} remaining)...")
    print(f"Estimated cost to finish: ~${remaining * 0.04:.2f} - ${remaining * 0.06:.2f} (at ~$9/M tokens)")
    print()

    total_tokens_used = 0
    total_cost = 0.0

    for i, img_path in enumerate(image_files, 1):
        page_index = int(img_path.stem.split('_page_')[1])
        txt_path = OCR_DIR / f"{PDF_STEM}_page_{page_index:03d}.txt"

        if txt_path.exists():
            print(f"  [{i}/{total}] Page {img_path.stem} already OCR'd, skipping")
            continue

        print(f"  [{i}/{total}] OCR page {img_path.stem}...", end=" ", flush=True)

        try:
            result = get_gemini_ocr(str(img_path), api_key=api_key)

            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(result["text"])

            total_tokens_used += result["total_tokens"]
            total_cost += result["estimated_cost"]

            mark_page_done(
                pdf_name=PDF_NAME,
                page_number=page_index,
                ocr_text_path=str(txt_path),
                prompt_tokens=result["prompt_tokens"],
                completion_tokens=result["completion_tokens"],
                total_tokens=result["total_tokens"],
                estimated_cost=result["estimated_cost"],
                db_path=PIPELINE_DB,
            )

            print(f"OK ({result['total_tokens']} tokens, ${result['estimated_cost']:.4f})")

        except Exception as e:
            print(f"ERROR: {e}")
            mark_page_failed(
                pdf_name=PDF_NAME,
                page_number=page_index,
                error_message=str(e),
                db_path=PIPELINE_DB,
            )
            # Save error file
            error_path = OCR_DIR / f"{PDF_STEM}_page_{page_index:03d}.error.txt"
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(str(e))

    print(f"\nOCR complete. Total tokens: {total_tokens_used}, Total cost: ${total_cost:.4f}")
    progress = get_pdf_progress(PDF_NAME, PIPELINE_DB)
    print(f"Tracker status: {progress['done']}/{progress['total_pages']} done, "
          f"{progress['failed']} failed, {progress['pending']} pending\n")


def generate_json():
    """Parse OCR output into structured JSON for frontend."""
    print("Parsing OCR output into structured JSON...")

    debate_data = parse_pdf_debates(
        ocr_dir=OCR_DIR,
        pdf_name=PDF_NAME,
        date=SESSION_DATE,
        session_title=SESSION_TITLE,
        output_path=OUTPUT_JSON
    )

    print(f"Generated {OUTPUT_JSON}")
    print(f"  Pages: {debate_data['total_pages']}")
    print(f"  Speakers: {len(debate_data['speakers'])}")
    print()


def main():
    print("=" * 60)
    print("Devanagari Parliamentary Debate OCR Pipeline")
    print("=" * 60)
    print()
    
    convert_pdf_to_images()
    run_ocr()
    generate_json()
    
    print("Pipeline complete!")
    print(f"Frontend data saved to: {OUTPUT_JSON}")
    print("Run 'cd frontend && npm run build' to rebuild the site.")


if __name__ == "__main__":
    main()
