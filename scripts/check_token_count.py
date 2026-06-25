"""Check token counts for input text across DeepSeek models via OpenRouter.

This script makes a minimal chat-completion request to each model and reports
the prompt-token count returned in the API usage field. Because tokenizers are
model-specific, the same text may be split into a different number of tokens by
different models.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODELS = [
    "deepseek/deepseek-v4-flash",  # DeepSeek V4 Flash (fast / efficient)
]


def get_token_count(
    text: str,
    model: str,
    api_key: Optional[str] = None,
    system_message: Optional[str] = None,
    api_url: str = API_URL,
) -> int:
    """Return prompt token count for ``text`` according to ``model``.

    A single-token completion is requested so the call is cheap; only the
    ``prompt_tokens`` value from the usage field is returned.

    Args:
        text: Input text to tokenize.
        model: OpenRouter model identifier.
        api_key: OpenRouter API key. Defaults to ``OPENROUTER_API_KEY`` env var.
        system_message: Optional system message to include.
        api_url: OpenRouter completions endpoint.

    Returns:
        Number of prompt tokens reported by the API.

    Raises:
        ValueError: If no API key is available.
        requests.HTTPError: If the API request fails.
    """
    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenRouter API key not found. Set OPENROUTER_API_KEY in your environment."
        )

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": text})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1,
        "temperature": 0.0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(api_url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens")
    if prompt_tokens is None:
        raise RuntimeError(f"API response did not include usage.prompt_tokens: {data}")

    return int(prompt_tokens)


def read_input(source: Optional[str]) -> str:
    """Read input text from a file path, raw string, or stdin."""
    if source is None:
        return sys.stdin.read()

    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")

    return source


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check prompt-token counts for text across DeepSeek models via OpenRouter."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input text, file path, or omit to read from stdin.",
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="OpenRouter model identifier (can be given multiple times).",
    )
    parser.add_argument(
        "--system",
        default=None,
        help="Optional system message to include before the input text.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="OpenRouter API key (default: OPENROUTER_API_KEY env var).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of a formatted table.",
    )

    args = parser.parse_args(argv)

    models = args.models or DEFAULT_MODELS
    text = read_input(args.input)

    if not text.strip():
        print("Error: Input text is empty.", file=sys.stderr)
        return 1

    results = {}
    errors = {}

    for model in models:
        try:
            count = get_token_count(
                text,
                model,
                api_key=args.api_key,
                system_message=args.system,
            )
            results[model] = count
        except Exception as exc:
            errors[model] = str(exc)

    if args.json:
        import json

        output = {
            "input_length_chars": len(text),
            "input_length_words": len(text.split()),
            "token_counts": results,
            "errors": errors,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"Input length: {len(text):,} characters, {len(text.split()):,} words\n")
        print(f"{'Model':<40} {'Prompt Tokens':>15}")
        print("-" * 58)
        for model in models:
            if model in results:
                print(f"{model:<40} {results[model]:>15,}")
            else:
                print(f"{model:<40} {'ERROR':>15}")
        if errors:
            print()
            for model, msg in errors.items():
                print(f"Error for {model}: {msg}", file=sys.stderr)

    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
