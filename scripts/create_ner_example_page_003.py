"""Generate a manually-verified NER gold example for page 003.

Page 003 is a printed member list. Each non-empty line contains either:
  - a header element (page number, house name, date)
  - a section marker ([स्तम्भ १], [स्तम्भ २])
  - one member entry (name + optional trailing honorific/title)

We label each member entry as PERSON and structural tokens as ORG / DATE / NUMBER.
"""

import json
from pathlib import Path

from scripts.ner_indexer import index_ocr_page_for_ner

TXT_PATH = Path(
    "C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2/1952_1_100_2_page_003.txt"
)
OUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/ner_examples")
OUT_PATH = OUT_DIR / "page_003_output.json"


def is_header_token(word: str) -> bool:
    """Return True if the token is part of the page header."""
    return word in {"**१८]**", "**विधान", "सभा**", "**[७", "मार्च,", "१९५२**"}


def is_section_marker(line_words: list) -> bool:
    """Return True if the line is [स्तम्भ १] or [स्तम्भ २]."""
    if not line_words:
        return False
    first = line_words[0]["text"]
    return first in {"**[स्तम्भ", "[स्तम्भ"}


def annotate_page_003() -> dict:
    """Create NER annotations for page 003 using original line boundaries."""
    page_data = index_ocr_page_for_ner(TXT_PATH)
    all_words = page_data["words"]
    text = TXT_PATH.read_text(encoding="utf-8")

    entities = []
    word_idx = 0

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # Count how many tokens this line contributes
        line_words = []
        tokens_in_line = len(line.split())
        for _ in range(tokens_in_line):
            if word_idx < len(all_words):
                line_words.append(all_words[word_idx])
                word_idx += 1

        if not line_words:
            continue

        first_text = line_words[0]["text"]

        # Header line: १८] विधान सभा [७ मार्च, १९५२
        if is_header_token(first_text):
            for j, w in enumerate(line_words):
                txt = w["text"]
                if txt == "**१८]**":
                    entities.append(
                        {
                            "label": "NUMBER",
                            "start": w["index"],
                            "end": w["index"],
                            "text": txt,
                        }
                    )
                elif txt == "**विधान":
                    if j + 1 < len(line_words):
                        entities.append(
                            {
                                "label": "ORG",
                                "start": w["index"],
                                "end": line_words[j + 1]["index"],
                                "text": f"{txt} {line_words[j + 1]['text']}",
                            }
                        )
                elif txt == "**[७":
                    if j + 2 < len(line_words):
                        entities.append(
                            {
                                "label": "DATE",
                                "start": w["index"],
                                "end": line_words[j + 2]["index"],
                                "text": f"{txt} {line_words[j + 1]['text']} {line_words[j + 2]['text']}",
                            }
                        )
            continue

        # Section marker line: [स्तम्भ १] / [स्तम्भ २]
        if is_section_marker(line_words):
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = annotate_page_003()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(result['entities'])} NER annotations to {OUT_PATH}")


if __name__ == "__main__":
    main()
