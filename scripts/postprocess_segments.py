"""Post-process LLM-parsed segments to clean text and normalize structure.

This script transforms the raw LLM output JSON into cleaner, UI-ready segments:

1. Removes markdown/table artifacts from all segment text.
2. Converts chair announcements into speech segments with speaker set to
   'माननीय अध्यक्ष' and removes that prefix from the speech body.
3. Cleans member-list headers and table syntax.
4. Removes honorific prefixes from speech speaker names where appropriate.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

INPUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/llm_parsed")
OUTPUT_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/data/llm_parsed_clean")

# Honorifics that commonly precede or follow names in parliamentary records.
HONORIFICS = {"श्री", "श्रीमती", "माननीय", "डा०", "प्रो०", "स्व०"}


def clean_text(text: str) -> str:
    """Aggressively clean markdown and table artifacts."""
    if not text:
        return ""

    # Remove markdown bold/italic markers
    text = text.replace("**", " ")
    text = text.replace("__", " ")
    text = text.replace("*", " ")

    # Remove markdown heading markers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Remove table syntax fragments
    text = text.replace("|", " ")
    text = text.replace(":---", " ")
    text = re.sub(r"-{3,}", " ", text)

    # Remove structural brackets
    text = text.replace("[", " ").replace("]", " ")

    # Remove stray underscores used for markdown emphasis
    text = re.sub(r"(?<!\\)_", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_chair_text(text: str) -> bool:
    """Return True if the text is a chair announcement/procedural text."""
    return "माननीय अध्यक्ष" in text or "अध्यक्ष" in text[:50]


def extract_chair_speaker(text: str) -> tuple[str, str]:
    """Return (speaker, cleaned_text) for chair-related text."""
    speaker = "माननीय अध्यक्ष"
    # Remove all occurrences of 'माननीय अध्यक्ष' from text body to avoid redundancy
    cleaned = text.replace("माननीय अध्यक्ष", " ")
    # Clean up leftover punctuation/whitespace
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s+", ", ", cleaned)
    cleaned = cleaned.strip(" ,।")
    return speaker, cleaned


def clean_speaker_name(name: str) -> str:
    """Clean and normalize speaker name."""
    if not name:
        return ""
    name = clean_text(name)
    # If name is just honorifics, return as-is
    if name in HONORIFICS or name == "माननीय अध्यक्ष":
        return name
    # Remove trailing/leading honorifics for cleaner display
    for h in sorted(HONORIFICS, key=len, reverse=True):
        name = re.sub(rf"^{h}\s+", "", name)
        name = re.sub(rf"\s+{h}$", "", name)
    return name.strip(" ,।")


def remove_member_list_header(text: str) -> str:
    """Remove header lines like 'उपस्थित सदस्यों की सूची (१८६)' from member list text."""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip obvious headers and table separators
        if re.search(r"उपस्थित|सूची|स्तम्भ|[:|_-]{2,}", line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def split_member_entries(text: str) -> List[Dict[str, str]]:
    """Split a member-list text into individual {name, honorific} entries."""
    # Treat 'माननीय श्री' as a single honorific token
    text = text.replace("माननीय श्री", "माननीय_श्री")
    tokens = text.split()

    entries: List[Dict[str, str]] = []
    current_name_tokens: List[str] = []

    HONORIFIC_TOKENS = {"श्री", "श्रीमती", "माननीय_श्री", "राजा", "नवाब"}

    for token in tokens:
        token = token.strip(" ,।")
        if not token:
            continue

        if token in HONORIFIC_TOKENS:
            if current_name_tokens:
                name = " ".join(current_name_tokens).strip(" ,।")
                honorific = token.replace("माननीय_श्री", "माननीय श्री")
                entries.append({"name": name, "honorific": honorific})
                current_name_tokens = []
        else:
            current_name_tokens.append(token)

    # Any leftover tokens without a trailing honorific
    if current_name_tokens:
        name = " ".join(current_name_tokens).strip(" ,।")
        entries.append({"name": name, "honorific": ""})

    return entries


def postprocess_page(page_data: Dict[str, Any]) -> Dict[str, Any]:
    """Post-process a single page's segments."""
    segments = page_data.get("segments", [])
    new_segments: List[Dict[str, Any]] = []

    for seg in segments:
        seg_type = seg.get("type", "narrative")
        text = clean_text(seg.get("text", ""))

        if not text:
            continue

        # Convert chair announcements/headings to speeches by माननीय अध्यक्ष
        if is_chair_text(text):
            speaker, body = extract_chair_speaker(text)
            if body:
                new_seg = {
                    "type": "speech",
                    "start_index": seg.get("start_index"),
                    "end_index": seg.get("end_index"),
                    "text": body,
                    "subtype": None,
                    "speaker": speaker,
                    "speaker_range": seg.get("speaker_range"),
                }
                new_segments.append(new_seg)
            continue

        # Clean member list text and split into structured entries
        if seg_type == "member_list":
            text = remove_member_list_header(text)
            if text:
                seg["text"] = text
                seg["members"] = split_member_entries(text)
                new_segments.append(seg)
            continue

        # Clean speech speaker and remove redundant honorific from text start
        if seg_type == "speech":
            speaker = clean_speaker_name(seg.get("speaker", ""))
            seg["speaker"] = speaker or "Unknown Speaker"
            # If text starts with the speaker's name, remove it to avoid duplication
            if speaker and text.startswith(speaker):
                text = text[len(speaker):].strip(" ,।:")
            seg["text"] = text
            new_segments.append(seg)
            continue

        # Default: just clean text
        seg["text"] = text
        new_segments.append(seg)

    page_data["segments"] = new_segments
    return page_data


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for page_file in sorted(INPUT_DIR.glob("page_*.json")):
        with open(page_file, "r", encoding="utf-8") as f:
            page_data = json.load(f)

        cleaned = postprocess_page(page_data)

        out_path = OUTPUT_DIR / page_file.name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

        print(f"Post-processed {page_file.name} -> {out_path}")


if __name__ == "__main__":
    main()
