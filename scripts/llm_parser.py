"""LLM-based parser for parliamentary transcripts using word-level indexing."""
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Segment types that must cover the whole page without overlap
SEGMENT_TYPES = {
    "metadata",
    "headings",
    "announcements",
    "speeches",
    "member_lists",
    "narrative",
}

TYPE_SINGULAR = {
    "metadata": "metadata",
    "headings": "heading",
    "announcements": "announcement",
    "speeches": "speech",
    "member_lists": "member_list",
    "narrative": "narrative",
}


def load_prompt_examples(examples_dir: Path) -> List[Dict[str, str]]:
    """Load example input/output pairs from a directory."""
    examples = []
    if not examples_dir.exists():
        return examples

    for inp_file in sorted(examples_dir.glob("*_input.txt")):
        name = inp_file.stem.replace("_input", "")
        out_file = examples_dir / f"{name}_output.json"
        if out_file.exists():
            examples.append({
                "input": inp_file.read_text(encoding="utf-8"),
                "output": out_file.read_text(encoding="utf-8"),
            })
    return examples


def build_llm_prompt(
    page_words: List[Dict[str, Any]],
    examples_dir: Path,
) -> str:
    """Build a few-shot prompt for the LLM using all examples in the directory."""
    examples = load_prompt_examples(examples_dir)

    prompt_parts = [
        "You are parsing a Hindi parliamentary transcript (OCR output) into structured segments.",
        "",
        "Each word of the page is numbered with a zero-based index. Return only index ranges for each segment type.",
        "",
        "## Segment types",
        "",
        "- metadata: Page header/footer, volume info, dates",
        "- headings: Section titles, bold/centered text",
        "- announcements: Chair/official announcements (often contain 'माननीय अध्यक्ष', 'घोषणा', formal language)",
        "- speeches: Words spoken by a member (starts with a name followed by --, —, or :)",
        "- member_lists: List of names without a clear speaker",
        "- narrative: Stage directions, procedural notes, parenthetical text",
        "",
        "## Rules",
        "",
        "1. Use inclusive [start, end] ranges.",
        "2. Every word index must belong to exactly one segment.",
        "3. A speech range must include the speaker name. Use speaker_range as a sub-range inside the main speech range.",
        "4. Announcements can have a subtype: 'chair', 'clerk', or 'bill'.",
        "5. Output ONLY valid JSON. No explanation.",
        "",
    ]

    for i, ex in enumerate(examples, 1):
        prompt_parts.extend([
            f"## Example {i}",
            "",
            "Input words:",
            ex["input"],
            "",
            "Expected output:",
            ex["output"],
            "",
        ])

    prompt_parts.extend([
        "Now parse this page:",
        format_wordlist(page_words),
        "",
        "Output only the JSON.",
    ])

    return "\n".join(prompt_parts)


def format_wordlist(words: List[Dict[str, Any]]) -> str:
    """Format indexed words for the prompt."""
    return "\n".join(f"{w['index']:03d}: {w['text']}" for w in words)


def call_llm(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    api_url: str = DEFAULT_API_URL,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    max_retries: int = 3,
) -> str:
    """Send prompt to LLM and return raw text response."""
    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise document parser. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    return ""


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract JSON object from LLM response, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    return json.loads(text)


def validate_llm_output(output: Dict[str, Any], total_words: int) -> List[str]:
    """Validate LLM output and return list of errors."""
    errors = []

    if "total_words" in output and output["total_words"] != total_words:
        errors.append(f"total_words mismatch: {output.get('total_words')} vs {total_words}")

    covered = [False] * total_words

    for key in SEGMENT_TYPES:
        for item in output.get(key, []):
            if isinstance(item, list):
                start, end = item
            elif isinstance(item, dict):
                start, end = item.get("range", [0, 0])
            else:
                errors.append(f"Unknown item type in {key}: {item}")
                continue

            if start < 0 or end >= total_words or start > end:
                errors.append(f"Invalid range in {key}: [{start}, {end}] for total_words={total_words}")
                continue

            for i in range(start, end + 1):
                if covered[i]:
                    errors.append(f"Overlapping coverage at index {i} in {key}")
                covered[i] = True

    uncovered = [i for i, v in enumerate(covered) if not v]
    if uncovered:
        errors.append(f"Uncovered word indices: {uncovered[:10]}{'...' if len(uncovered) > 10 else ''}")

    return errors


def parse_with_retry(
    page_words: List[Dict[str, Any]],
    examples_dir: Path,
    model: Optional[str] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Parse a page, retrying with feedback if validation fails."""
    prompt = build_llm_prompt(page_words, examples_dir)
    total_words = len(page_words)

    for attempt in range(max_retries + 1):
        raw_response = call_llm(prompt, model=model)
        try:
            llm_output = extract_json_from_response(raw_response)
        except json.JSONDecodeError as e:
            errors = [f"Invalid JSON: {e}"]
            if attempt == max_retries:
                raise ValueError(f"Failed to get valid JSON after {max_retries + 1} attempts") from e
            prompt = f"{prompt}\n\nYour previous response was not valid JSON. Fix it and output only valid JSON."
            continue

        errors = validate_llm_output(llm_output, total_words)
        if not errors:
            return llm_output

        if attempt < max_retries:
            error_text = "\n".join(f"- {e}" for e in errors)
            prompt = (
                f"{prompt}\n\n"
                f"Your previous output had these errors:\n{error_text}\n\n"
                f"Fix them and return the corrected JSON. Ensure every word index is covered exactly once."
            )

    # Return best-effort output if retries exhausted
    return llm_output


def clean_segment_text(text: str) -> str:
    """Clean raw segment text for UI display.

    Removes markdown formatting, table syntax, and normalizes whitespace.
    """
    # Remove markdown bold/italic markers
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("*", "")
    # Remove markdown heading markers
    text = re.sub(r"^#{1,6}\s*", "", text)
    # Remove table syntax fragments
    text = text.replace("|", " ")
    text = text.replace(":---", " ")
    text = re.sub(r"-{3,}", " ", text)
    # Remove stray brackets/parentheses that are structural artifacts
    text = text.replace("[", "").replace("]", "")
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def reconstruct_segments(
    page_words: List[Dict[str, Any]],
    llm_output: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert LLM index output into full text segments."""
    words = [w["text"] for w in page_words]
    segments = []
    order = []

    def add_segments(key: str, items: List[Any], default_subtype: Optional[str] = None):
        for item in items:
            if isinstance(item, list):
                start, end = item
                meta = {}
            elif isinstance(item, dict):
                start, end = item.get("range", [0, 0])
                meta = {k: v for k, v in item.items() if k != "range"}
            else:
                continue

            text = clean_segment_text(" ".join(words[start:end + 1]))
            segment = {
                "type": TYPE_SINGULAR[key],
                "start_index": start,
                "end_index": end,
                "text": text,
            }
            if default_subtype:
                segment["subtype"] = default_subtype
            if "subtype" in meta:
                segment["subtype"] = meta["subtype"]
            if "speaker_range" in meta:
                sr_start, sr_end = meta["speaker_range"]
                segment["speaker_range"] = [sr_start, sr_end]
                segment["speaker"] = " ".join(words[sr_start:sr_end + 1])

            segments.append(segment)
            order.append(start)

    # Process in a fixed order so we can sort later
    add_segments("metadata", llm_output.get("metadata", []))
    add_segments("headings", llm_output.get("headings", []))
    add_segments("announcements", llm_output.get("announcements", []))
    add_segments("speeches", llm_output.get("speeches", []))
    add_segments("member_lists", llm_output.get("member_lists", []))
    add_segments("narrative", llm_output.get("narrative", []))

    # Sort by start index to preserve reading order
    segments.sort(key=lambda x: x["start_index"])
    return segments
