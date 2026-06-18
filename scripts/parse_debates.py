"""Parse OCR text files into structured debate JSON for the frontend.

Input: Directory containing page_001.txt, page_002.txt, etc.
Output: JSON file with pages, each containing speeches with speaker attribution.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any


# Strict speaker pattern for Hindi parliamentary transcripts
# Matches lines that start with a speaker designation and are followed by
# a separator (—, –, --, or :)
SPEAKER_PATTERN = re.compile(
    r'^(?:\*\*)?\s*'
    r'(माननीय\s+)?'
    r'(अध्यक्ष|उपाध्यक्ष|श्रीमती|श्री|नवाब|राजा|महोदय)'
    r'\s*'
    r'([^\-—–:\n]{1,80}?)'
    r'(?:\s*\(([^)]+)\))?'
    r'\s*(?:\*\*)?\s*'
    r'[—–:-]+\s*',
    re.UNICODE
)

# Patterns that indicate text is NOT a speaker line
NOT_SPEAKER_PATTERNS = [
    re.compile(r'\(देखिये\s+नत्थी'),  # Footnotes
    re.compile(r'^\*\*'),              # Markdown headings
    re.compile(r'^\['),                # Section markers
    re.compile(r'^\('),                # Parenthetical notes
]


def unwrap_lines(text: str) -> str:
    """Unwrap hard line breaks inserted by OCR.

    OCR output often breaks lines every ~50-60 characters. Lines that do not
    end with sentence-ending punctuation are merged with the following line to
    form natural paragraphs that fill the full width of the page.
    """
    lines = [line.rstrip() for line in text.split('\n')]
    result: List[str] = []
    current: List[str] = []

    # Punctuation that indicates the end of a sentence/paragraph
    sentence_end = re.compile(r'[।!?.)\]]$')

    for line in lines:
        stripped = line.strip()

        # Preserve blank lines as paragraph separators
        if not stripped:
            if current:
                result.append(' '.join(current))
                current = []
            continue

        # Do not unwrap structural lines (headings, separators, tables, speakers)
        is_structural = (
            stripped.startswith('#')
            or stripped.startswith('**')
            or stripped.startswith('[')
            or stripped.startswith('---')
            or stripped.startswith('|')
            or bool(SPEAKER_PATTERN.match(stripped))
        )

        if is_structural:
            if current:
                result.append(' '.join(current))
                current = []
            result.append(line)
            continue

        current.append(stripped)

        # Finalize paragraph when sentence-ending punctuation is reached
        if sentence_end.search(stripped):
            result.append(' '.join(current))
            current = []

    if current:
        result.append(' '.join(current))

    return '\n'.join(result)


def normalize_text(text: str) -> str:
    """Clean up OCR text."""
    # Remove excessive whitespace
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove markdown table artifacts
    text = re.sub(r'\|.*\|', '', text)
    # Unwrap hard line breaks from OCR
    text = unwrap_lines(text)
    return text.strip()


def merge_consecutive_headers(paragraphs: List[str]) -> List[str]:
    """Merge consecutive short header lines into a single heading.

    E.g. ['# उत्तर प्रदेश विधान सभा', '# की', '# कार्यवाही']
    becomes ['# उत्तर प्रदेश विधान सभा की कार्यवाही'].

    Only merges when each component line is short (title-like), avoiding
    accidental merging of distinct section headings.
    """
    if not paragraphs:
        return paragraphs

    merged: List[str] = []
    i = 0
    n = len(paragraphs)

    while i < n:
        para = paragraphs[i]

        # Look for a markdown heading line that is short (title component)
        stripped = para.lstrip('#').strip()
        if para.startswith('#') and len(stripped) <= 40:
            header_parts = [stripped]
            j = i + 1
            while j < n:
                next_para = paragraphs[j]
                next_stripped = next_para.lstrip('#').strip()
                # Merge with another short heading component OR a very short joining word
                if (
                    next_para.startswith('#')
                    and len(next_stripped) <= 40
                ) or (
                    not next_para.startswith('#')
                    and len(next_para.strip()) <= 10
                ):
                    header_parts.append(next_stripped)
                    j += 1
                else:
                    break

            if len(header_parts) > 1:
                merged_text = ' '.join(header_parts).strip()
                merged.append(f'# {merged_text}')
                i = j
                continue

        merged.append(para)
        i += 1

    return merged


def is_likely_speaker_line(para: str) -> bool:
    """Check if a paragraph looks like a speaker attribution line."""
    # Must not be a footnote or heading
    for pattern in NOT_SPEAKER_PATTERNS:
        if pattern.search(para):
            return False
    
    # Must match the speaker pattern
    match = SPEAKER_PATTERN.match(para)
    if not match:
        return False
    
    # The speaker name part should be reasonably short
    full_speaker = match.group(2) + ' ' + match.group(3)
    if len(full_speaker.strip()) > 100:
        return False

    # Reject common false positives where श्री is fused with मान्/मन्
    # (e.g. "श्रीमन्, लोकतंत्रीय..." is speech text, not a speaker)
    name_part = (match.group(3) or '').strip()
    if name_part.startswith(('मन्', 'मान्')):
        return False

    # The text after separator should exist
    remaining = para[match.end():].strip()
    if not remaining:
        return False

    return True


def parse_speeches(text: str) -> List[Dict[str, Any]]:
    """Parse a page of OCR text into speaker-attributed speeches.
    
    Returns a list of dicts with keys: speaker, text, type.
    If no speaker is found, the whole text is treated as narrative.
    """
    text = normalize_text(text)
    if not text:
        return []
    
    speeches = []
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    paragraphs = merge_consecutive_headers(paragraphs)

    current_speaker = None
    current_text = []
    
    for para in paragraphs:
        match = SPEAKER_PATTERN.match(para)
        is_speaker = is_likely_speaker_line(para)
        
        if is_speaker and match:
            # Save previous speech if exists
            if current_speaker is not None and current_text:
                speeches.append({
                    "speaker": current_speaker,
                    "text": ' '.join(current_text).strip(),
                    "type": "speech"
                })
            
            # Build speaker name
            honorific = match.group(1) or ''
            title = match.group(2) or ''
            name = match.group(3) or ''
            qualifier = match.group(4) or ''
            
            speaker_parts = [p.strip() for p in [honorific, title, name] if p.strip()]
            current_speaker = ' '.join(speaker_parts)
            if qualifier:
                current_speaker += f' ({qualifier})'
            
            # Get the rest of the paragraph as speech text
            remaining = para[match.end():].strip()
            current_text = [remaining] if remaining else []
        else:
            # Determine block type
            is_heading = (
                para.startswith('#') or
                para.startswith('**') and para.endswith('**') or
                para.startswith('*') and para.endswith('*')
            )
            block_type = "heading" if is_heading else "narrative"

            # Strip leading markdown heading marker for display
            display_text = para
            if display_text.startswith('#'):
                display_text = display_text.lstrip('#').strip()

            # This paragraph continues the current speech or is narrative
            if current_speaker is not None and not is_heading:
                current_text.append(para)
            else:
                # Narrative text before any speaker, or a heading
                speeches.append({
                    "speaker": None,
                    "text": display_text,
                    "type": block_type
                })
    
    # Don't forget the last speech
    if current_speaker is not None and current_text:
        speeches.append({
            "speaker": current_speaker,
            "text": ' '.join(current_text).strip(),
            "type": "speech"
        })
    
    return speeches


def parse_pdf_debates(
    ocr_dir: Path,
    pdf_name: str,
    date: str,
    session_title: str,
    output_path: Path
) -> Dict[str, Any]:
    """Parse all OCR text files for a PDF into structured debate data.
    
    Args:
        ocr_dir: Directory containing page_001.txt, page_002.txt, etc.
        pdf_name: Name of the source PDF
        date: Date of the session (YYYY-MM-DD)
        session_title: Title of the session
        output_path: Where to save the output JSON
    
    Returns:
        Structured debate data dict
    """
    pages = []
    all_speakers = set()

    # Look for OCR text files. Supports both legacy `page_NNN.txt` and
    # new `{pdf_name}_page_NNN.txt` naming.
    txt_files = sorted(ocr_dir.glob("page_*.txt")) + sorted(
        ocr_dir.glob(f"{pdf_name.replace('.pdf', '')}_page_*.txt")
    )

    for txt_file in txt_files:
        # Skip error files like page_032.error.txt
        if ".error" in txt_file.name:
            continue

        stem = txt_file.stem
        if stem.startswith("page_"):
            page_num = int(stem.split('_')[1])
        else:
            page_num = int(stem.split('_page_')[1])

        with open(txt_file, 'r', encoding='utf-8') as f:
            text = f.read()

        speeches = parse_speeches(text)
        
        # Collect speakers
        for speech in speeches:
            if speech.get("speaker"):
                all_speakers.add(speech["speaker"])
        
        # Determine corresponding image name
        if txt_file.stem.startswith("page_"):
            image_name = f"page_{page_num:03d}.png"
        else:
            image_name = f"{txt_file.stem.split('_page_')[0]}_page_{page_num:03d}.png"

        pages.append({
            "page_number": page_num,
            "image": image_name,
            "speeches": speeches
        })
    
    debate_data = {
        "pdf_name": pdf_name,
        "date": date,
        "session_title": session_title,
        "total_pages": len(pages),
        "speakers": sorted(list(all_speakers)),
        "pages": pages
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(debate_data, f, ensure_ascii=False, indent=2)
    
    return debate_data


def main():
    """Example usage."""
    ocr_dir = Path("C:/Users/adity/Desktop/ocr_devnagri/data/full_pdf_ocr/1952_1_100_2")
    output_path = Path("C:/Users/adity/Desktop/ocr_devnagri/frontend/public/data/debates.json")

    debate_data = parse_pdf_debates(
        ocr_dir=ocr_dir,
        pdf_name="1952_1_100_2.pdf",
        date="1952-03-07",
        session_title="उत्तर प्रदेश विधान सभा - 7 मार्च 1952",
        output_path=output_path
    )
    
    print(f"Parsed {debate_data['total_pages']} pages")
    print(f"Found {len(debate_data['speakers'])} speakers")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
