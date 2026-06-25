"""LLM-based Named Entity Recognition (NER) parser for parliamentary transcripts.

The parser takes a 1-based indexed wordlist for a page and asks the LLM to
return index ranges for named entities. Currently supported labels:

    PERSON  : member names (including attached honorifics/titles)
    ORG     : organization names (e.g., विधान सभा)
    DATE    : dates (e.g., ७ मार्च, १९५२)
    NUMBER  : standalone numbers / section markers (e.g., १८, [स्तम्भ १])
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from scripts.ner_indexer import format_ner_wordlist, index_ocr_page_for_ner

load_dotenv()

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"

VALID_LABELS = {"PERSON", "ORG", "DATE", "NUMBER"}


def load_ner_examples(examples_dir: Path) -> List[Dict[str, str]]:
    """Load example input/output pairs for NER few-shot prompting."""
    examples = []
    if not examples_dir.exists():
        return examples

    for inp_file in sorted(examples_dir.glob("*_input.txt")):
        name = inp_file.stem.replace("_input", "")
        out_file = examples_dir / f"{name}_output.json"
        if out_file.exists():
            examples.append(
                {
                    "input": inp_file.read_text(encoding="utf-8"),
                    "output": out_file.read_text(encoding="utf-8"),
                }
            )
    return examples


def build_ner_prompt(
    page_words: List[Dict[str, Any]],
    examples_dir: Path,
) -> str:
    """Build a few-shot prompt for NER using all examples in the directory."""
    examples = load_ner_examples(examples_dir)

    prompt_parts = [
        "You are performing Named Entity Recognition (NER) on a Hindi parliamentary document.",
        "",
        "Each word of the page is numbered with a one-based index in the format word##index.",
        "Return ONLY a JSON object with an 'entities' array. Each entity must have:",
        "  - label: one of PERSON, ORG, DATE, NUMBER",
        "  - start: index of the first word (inclusive)",
        "  - end: index of the last word (inclusive)",
        "  - text (optional): the covered text for verification",
        "",
        "Rules:",
        "1. Use one-based indices exactly as shown in the input.",
        "2. Every member name line should be a single PERSON entity, including trailing honorifics like श्री / श्रीमती / राजा / नवाब.",
        "3. Structural/header tokens should be labelled ORG, DATE, or NUMBER.",
        "4. Do not overlap entities.",
        "5. Output ONLY valid JSON. No explanation.",
        "",
    ]

    for i, ex in enumerate(examples, 1):
        prompt_parts.extend(
            [
                f"## Example {i}",
                "",
                "Input words:",
                ex["input"],
                "",
                "Expected output:",
                ex["output"],
                "",
            ]
        )

    prompt_parts.extend(
        [
            "Now annotate this page:",
            format_ner_wordlist(page_words),
            "",
            "Output only the JSON.",
        ]
    )

    return "\n".join(prompt_parts)


def call_llm(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    api_url: str = DEFAULT_API_URL,
    temperature: float = 0.0,
    max_tokens: int = 2048,
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
            {
                "role": "system",
                "content": "You are a precise document NER annotator. Output only valid JSON.",
            },
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


def validate_ner_output(
    output: Dict[str, Any], total_words: int
) -> List[str]:
    """Validate NER output and return list of errors."""
    errors = []

    if "entities" not in output:
        errors.append("Missing 'entities' key")
        return errors

    if not isinstance(output["entities"], list):
        errors.append("'entities' must be a list")
        return errors

    covered = [False] * (total_words + 1)  # 1-based indexing

    for idx, entity in enumerate(output["entities"]):
        label = entity.get("label")
        start = entity.get("start")
        end = entity.get("end")

        if label not in VALID_LABELS:
            errors.append(f"Entity {idx}: invalid label '{label}'")

        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"Entity {idx}: start/end must be integers")
            continue

        if start < 1 or end > total_words or start > end:
            errors.append(
                f"Entity {idx}: invalid range [{start}, {end}] for total_words={total_words}"
            )
            continue

        for i in range(start, end + 1):
            if covered[i]:
                errors.append(f"Entity {idx}: overlapping coverage at index {i}")
            covered[i] = True

    return errors


def parse_with_retry(
    page_words: List[Dict[str, Any]],
    examples_dir: Path,
    model: Optional[str] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Parse a page, retrying with feedback if validation fails."""
    prompt = build_ner_prompt(page_words, examples_dir)
    total_words = len(page_words)

    for attempt in range(max_retries + 1):
        raw_response = call_llm(prompt, model=model)
        try:
            llm_output = extract_json_from_response(raw_response)
        except json.JSONDecodeError as e:
            if attempt == max_retries:
                raise ValueError(
                    f"Failed to get valid JSON after {max_retries + 1} attempts"
                ) from e
            prompt = f"{prompt}\n\nYour previous response was not valid JSON. Fix it and output only valid JSON."
            continue

        errors = validate_ner_output(llm_output, total_words)
        if not errors:
            return llm_output

        if attempt < max_retries:
            error_text = "\n".join(f"- {e}" for e in errors)
            prompt = (
                f"{prompt}\n\n"
                f"Your previous output had these errors:\n{error_text}\n\n"
                f"Fix them and return the corrected JSON. Ensure every entity has a valid label and range."
            )

    return llm_output
