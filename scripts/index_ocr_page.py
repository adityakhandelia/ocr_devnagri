"""Convert OCR text into indexed word lists for LLM-based parliamentary parsing."""
from pathlib import Path
from typing import Dict, List


def index_ocr_text(text: str) -> List[Dict[str, any]]:
    """Split OCR text into words and assign zero-based indices.

    Whitespace is normalized and empty tokens are dropped. Punctuation and
    separators remain attached to words so the LLM can use context.
    """
    words = []
    for line in text.split('\n'):
        for token in line.split():
            token = token.strip()
            if token:
                words.append({'index': len(words), 'text': token})
    return words


def index_ocr_file(txt_path: Path) -> Dict[str, any]:
    """Read an OCR text file and return indexed words plus metadata."""
    text = txt_path.read_text(encoding='utf-8')
    words = index_ocr_text(text)
    return {
        'page_number': _extract_page_number(txt_path),
        'pdf_name': None,
        'total_words': len(words),
        'words': words,
    }


def _extract_page_number(txt_path: Path) -> int:
    """Extract page number from filename like page_009.txt or 1952_1_100_2_page_009.txt."""
    stem = txt_path.stem
    if '_page_' in stem:
        num_part = stem.split('_page_')[1]
    elif stem.startswith('page_'):
        num_part = stem.split('_')[1]
    else:
        return 0
    return int(num_part.split('.')[0])


def format_wordlist(words: List[Dict[str, any]]) -> str:
    """Format indexed words as a string suitable for the LLM prompt."""
    lines = []
    for w in words:
        lines.append(f"{w['index']:03d}: {w['text']}")
    return '\n'.join(lines)
