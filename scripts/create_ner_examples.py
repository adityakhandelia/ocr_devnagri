"""Generate NER gold examples for simple member-list pages.

A "simple" member-list page has one member entry per non-empty line. Header lines
and section markers are labelled as ORG / DATE / NUMBER.

Usage:
    uv run python scripts/create_ner_examples.py --page 3 --page 4
"""

import argparse
import json
from pathlib import Path

from scripts.ner_indexer import index_ocr_page_for_ner

OCR_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2")
OUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/ner_examples")


def is_header_line(line: str) -> bool:
    """Heuristic: lines that are clearly headers, not member names."""
    stripped = line.strip()
    header_markers = [
        "विधान सभा",
        "उत्तर प्रदेश",
        "उपस्थित सदस्यों",
        "स्तम्भ",
        "---",
        "|",
        "# ",
        "### ",
    ]
    return any(marker in stripped for marker in header_markers)


def is_section_marker_line(line: str) -> bool:
    """Return True if line is [स्तम्भ N]."""
    return "स्तम्भ" in line and "[" in line


def annotate_simple_page(txt_path: Path) -> dict:
    """Create line-based NER annotations for a simple member-list page."""
    page_data = index_ocr_page_for_ner(txt_path)
    all_words = page_data["words"]
    text = txt_path.read_text(encoding="utf-8")

    entities = []
    word_idx = 0

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        line_words = []
        tokens_in_line = len(line.split())
        for _ in range(tokens_in_line):
            if word_idx < len(all_words):
                line_words.append(all_words[word_idx])
                word_idx += 1

        if not line_words:
            continue

        if is_header_line(line):
            # Try to label known structural spans inside the header line
            for j, w in enumerate(line_words):
                txt = w["text"]
                if txt in {"**१८]**", "**[स्तम्भ", "[स्तम्भ"}:
                    # NUMBER for page/section markers
                    end_j = j
                    if j + 1 < len(line_words):
                        end_j = j + 1
                    entities.append(
                        {
                            "label": "NUMBER",
                            "start": line_words[j]["index"],
                            "end": line_words[end_j]["index"],
                            "text": " ".join(
                                line_words[k]["text"] for k in range(j, end_j + 1)
                            ),
                        }
                    )
                elif txt == "**विधान" or txt == "विधान":
                    end_j = j + 1
                    if end_j < len(line_words):
                        entities.append(
                            {
                                "label": "ORG",
                                "start": line_words[j]["index"],
                                "end": line_words[end_j]["index"],
                                "text": " ".join(
                                    line_words[k]["text"] for k in range(j, end_j + 1)
                                ),
                            }
                        )
                elif txt == "**[७" or txt == "[७":
                    end_j = min(j + 2, len(line_words) - 1)
                    entities.append(
                        {
                            "label": "DATE",
                            "start": line_words[j]["index"],
                            "end": line_words[end_j]["index"],
                            "text": " ".join(
                                line_words[k]["text"] for k in range(j, end_j + 1)
                            ),
                        }
                    )
                elif txt == "**शुक्रवार," or txt == "शुक्रवार,":
                    end_j = min(j + 2, len(line_words) - 1)
                    entities.append(
                        {
                            "label": "DATE",
                            "start": line_words[j]["index"],
                            "end": line_words[end_j]["index"],
                            "text": " ".join(
                                line_words[k]["text"] for k in range(j, end_j + 1)
                            ),
                        }
                    )
            continue

        if is_section_marker_line(line):
            entities.append(
                {
                    "label": "NUMBER",
                    "start": line_words[0]["index"],
                    "end": line_words[-1]["index"],
                    "text": " ".join(w["text"] for w in line_words),
                }
            )
            continue

        # Member entry: label the whole line as PERSON
        entities.append(
            {
                "label": "PERSON",
                "start": line_words[0]["index"],
                "end": line_words[-1]["index"],
                "text": " ".join(w["text"] for w in line_words),
            }
        )

    entities.sort(key=lambda e: (e["start"], e["end"]))

    return {
        "page_number": page_data["page_number"],
        "total_words": page_data["total_words"],
        "entities": entities,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate NER gold examples")
    parser.add_argument(
        "--page",
        action="append",
        type=int,
        dest="pages",
        help="Page number to annotate (can be repeated)",
    )
    args = parser.parse_args()

    pages = args.pages or [3]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for page_num in pages:
        txt_path = OCR_DIR / f"1952_1_100_2_page_{page_num:03d}.txt"
        if not txt_path.exists():
            txt_path = OCR_DIR / f"page_{page_num:03d}.txt"
        if not txt_path.exists():
            print(f"OCR text not found for page {page_num}")
            continue

        result = annotate_simple_page(txt_path)
        out_path = OUT_DIR / f"page_{page_num:03d}_output.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Also write indexed input if not present
        inp_path = OUT_DIR / f"page_{page_num:03d}_input.txt"
        if not inp_path.exists():
            from scripts.ner_indexer import format_ner_wordlist

            page_data = index_ocr_page_for_ner(txt_path)
            inp_path.write_text(format_ner_wordlist(page_data["words"]), encoding="utf-8")

        print(
            f"Page {page_num}: saved {len(result['entities'])} entities to {out_path}"
        )


if __name__ == "__main__":
    main()
