"""Indexed wordlist formatter for NER tasks.

Produces a 1-based indexed representation of an OCR page where each word is
followed by ##index. The output format matches the user's manual marking style:

    **१८]**##1 **विधान##2 सभा**##3 **[७##4 मार्च,##5 १९५२**##6
"""

import re
from pathlib import Path
from typing import Dict, List

from scripts.index_ocr_page import index_ocr_file, index_ocr_text


PUNCTUATION_PAIR = re.compile(r"^([(\[{}]+)(.+?)([)\]}।,]+)$")


def split_tokens_with_indices(text: str) -> List[Dict[str, any]]:
    """Split OCR text into 1-based indexed tokens.

    Punctuation markers such as '**', '[', ']', '(', ')', '।' and ',' are kept
    attached to their neighboring words so the indices match the visual layout.
    """
    words = []
    for line in text.split("\n"):
        for token in line.split():
            token = token.strip()
            if token:
                words.append({"index": len(words) + 1, "text": token})
    return words


def format_ner_wordlist(words: List[Dict[str, any]]) -> str:
    """Format indexed words using ##index suffixes.

    Args:
        words: List of dicts with 'index' (1-based) and 'text' keys.

    Returns:
        Single string with words separated by spaces and each word followed by
        ##index.
    """
    return " ".join(f"{w['text']}##{w['index']}" for w in words)


def index_ocr_page_for_ner(txt_path: Path) -> Dict[str, any]:
    """Read an OCR page and return 1-based indexed words plus metadata."""
    text = txt_path.read_text(encoding="utf-8")
    words = split_tokens_with_indices(text)
    return {
        "page_number": _extract_page_number(txt_path),
        "pdf_name": None,
        "total_words": len(words),
        "words": words,
    }


def _extract_page_number(txt_path: Path) -> int:
    """Extract page number from filename."""
    stem = txt_path.stem
    if "_page_" in stem:
        num_part = stem.split("_page_")[1]
    elif stem.startswith("page_"):
        num_part = stem.split("_")[1]
    else:
        return 0
    return int(num_part.split(".")[0])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate NER-indexed wordlist for a page")
    parser.add_argument("page", type=int, help="Page number to index")
    parser.add_argument(
        "--ocr-dir",
        type=str,
        default="C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2",
        help="Directory containing OCR text files",
    )
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()

    ocr_dir = Path(args.ocr_dir)
    txt_path = ocr_dir / f"1952_1_100_2_page_{args.page:03d}.txt"
    if not txt_path.exists():
        txt_path = ocr_dir / f"page_{args.page:03d}.txt"

    if not txt_path.exists():
        raise FileNotFoundError(f"OCR text not found for page {args.page}: {txt_path}")

    page_data = index_ocr_page_for_ner(txt_path)
    wordlist = format_ner_wordlist(page_data["words"])

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(wordlist, encoding="utf-8")
        print(f"Saved indexed wordlist to {out_path}")
    else:
        print(wordlist)

    print(f"\nTotal words: {page_data['total_words']}")
