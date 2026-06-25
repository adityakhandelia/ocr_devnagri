"""Generate NER gold example for page 002 (markdown table member list)."""

import json
import re
from pathlib import Path

from scripts.ner_indexer import index_ocr_page_for_ner

TXT_PATH = Path(
    "C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2/1952_1_100_2_page_002.txt"
)
OUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/ner_examples")
OUT_PATH = OUT_DIR / "page_002_output.json"


def annotate_page_002() -> dict:
    """Create NER annotations for page 002."""
    page_data = index_ocr_page_for_ner(TXT_PATH)
    all_words = page_data["words"]
    text = TXT_PATH.read_text(encoding="utf-8")

    entities = []
    word_idx = 0

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # Count tokens in this line
        line_words = []
        tokens_in_line = len(line.split())
        for _ in range(tokens_in_line):
            if word_idx < len(all_words):
                line_words.append(all_words[word_idx])
                word_idx += 1

        if not line_words:
            continue

        # Skip table separators and empty cells
        if line.replace("|", "").strip() == "" or "---" in line:
            continue

        # Header/title lines (not table data rows)
        first_text = line_words[0]["text"]
        if first_text.startswith("#") or first_text == "###":
            continue
        if "उपस्थित" in line or "सूची" in line or "उत्तर" in line and "विधान" in line:
            continue

        # Date line: **शुक्रवार, ७ मार्च, १९५२ ई०**
        if "शुक्रवार" in line or "मार्च" in line:
            entities.append(
                {
                    "label": "DATE",
                    "start": line_words[0]["index"],
                    "end": line_words[-1]["index"],
                    "text": " ".join(w["text"] for w in line_words),
                }
            )
            continue

        # Chair/official line: **विधान सभा की बैठक ... माननीय अध्यक्ष, श्री नफ़ीसुल हसन ...**
        if "बैठक" in line or "अध्यक्ष" in line:
            # Label the chair person as PERSON
            # Find "श्री" followed by name words before "की"
            for j, w in enumerate(line_words):
                if w["text"] in {"श्री", "माननीय"}:
                    # Look ahead for name span until a non-name token
                    name_start = j
                    name_end = j
                    while name_end + 1 < len(line_words):
                        nxt = line_words[name_end + 1]["text"]
                        if nxt in {"की", "अध्यक्षता", "में", "आरम्भ", "हुई", "।"}:
                            break
                        name_end += 1
                    if name_end > name_start:
                        entities.append(
                            {
                                "label": "PERSON",
                                "start": line_words[name_start]["index"],
                                "end": line_words[name_end]["index"],
                                "text": " ".join(
                                    line_words[k]["text"] for k in range(name_start, name_end + 1)
                                ),
                            }
                        )
            continue

        # Table data row: split by | to find cells
        cell_texts = [c.strip() for c in line.split("|")]
        # Remove empty cells
        cell_texts = [c for c in cell_texts if c]

        # Each non-empty cell should contain one bold member entry
        for cell in cell_texts:
            # Strip markdown bold
            cell = cell.strip()
            if not cell:
                continue
            cell = re.sub(r"^\*\*|\*\*$", "", cell).strip()
            if not cell:
                continue

            # Find this cell's words in the line_words sequence
            # Simple approach: consume tokens matching cell content
            cell_tokens = cell.split()
            if not cell_tokens:
                continue

            # Find start token matching first cell token
            start_pos = None
            for j, w in enumerate(line_words):
                cleaned = w["text"].lstrip("*").rstrip("*")
                if cleaned == cell_tokens[0]:
                    # Verify following tokens match
                    match = True
                    for k, ct in enumerate(cell_tokens):
                        if j + k >= len(line_words):
                            match = False
                            break
                        w_clean = line_words[j + k]["text"].lstrip("*").rstrip("*")
                        if w_clean != ct:
                            match = False
                            break
                    if match:
                        start_pos = j
                        break

            if start_pos is None:
                continue

            end_pos = start_pos + len(cell_tokens) - 1
            entities.append(
                {
                    "label": "PERSON",
                    "start": line_words[start_pos]["index"],
                    "end": line_words[end_pos]["index"],
                    "text": " ".join(
                        line_words[k]["text"] for k in range(start_pos, end_pos + 1)
                    ),
                }
            )

    entities.sort(key=lambda e: (e["start"], e["end"]))

    return {
        "page_number": page_data["page_number"],
        "total_words": page_data["total_words"],
        "entities": entities,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = annotate_page_002()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Write input if not present
    inp_path = OUT_DIR / "page_002_input.txt"
    if not inp_path.exists():
        from scripts.ner_indexer import format_ner_wordlist

        page_data = index_ocr_page_for_ner(TXT_PATH)
        inp_path.write_text(format_ner_wordlist(page_data["words"]), encoding="utf-8")

    print(f"Saved {len(result['entities'])} NER annotations to {OUT_PATH}")


if __name__ == "__main__":
    main()
