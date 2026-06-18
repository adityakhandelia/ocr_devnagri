"""Generate frontend JSON from existing OCR files only (no API calls)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.parse_debates import parse_pdf_debates

OCR_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2")
OUTPUT_JSON = Path("C:/Users/adity/Desktop/ocr_devnagri/frontend/public/data/debates.json")

if __name__ == "__main__":
    debate_data = parse_pdf_debates(
        ocr_dir=OCR_DIR,
        pdf_name="1952_1_100_2.pdf",
        date="1952-03-07",
        session_title="उत्तर प्रदेश विधान सभा - 7 मार्च 1952",
        output_path=OUTPUT_JSON
    )
    
    print(f"Generated {OUTPUT_JSON}")
    print(f"  Pages: {debate_data['total_pages']}")
    print(f"  Speakers: {len(debate_data['speakers'])}")
    print(f"  Sample speakers: {', '.join(debate_data['speakers'][:10])}")
