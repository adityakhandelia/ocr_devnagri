"""Build the LLM prompt by substituting example pages into the template."""
from pathlib import Path

TEMPLATE_PATH = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/llm_prompt_template_v2.txt")
EXAMPLES_DIR = Path("C:/Users/adity/Desktop/ocr_devnagri/scripts/llm_examples")


def load_examples():
    """Load all example input/output pairs from llm_examples directory."""
    examples = []
    for inp_file in sorted(EXAMPLES_DIR.glob("*_input.txt")):
        name = inp_file.stem.replace("_input", "")
        out_file = EXAMPLES_DIR / f"{name}_output.json"
        if out_file.exists():
            examples.append({
                "input": inp_file.read_text(encoding="utf-8"),
                "output": out_file.read_text(encoding="utf-8"),
            })
    return examples


def build_prompt_for_page(page_words_text: str) -> str:
    """Substitute examples and target page into the prompt template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    examples = load_examples()

    # Build examples section
    examples_text = []
    for i, ex in enumerate(examples, 1):
        examples_text.append(f"## Example {i}\n")
        examples_text.append("Input words:")
        examples_text.append(ex["input"])
        examples_text.append("")
        examples_text.append("Expected output:")
        examples_text.append(ex["output"])
        examples_text.append("")

    prompt = template.replace("[EXAMPLES_PLACEHOLDER]", "\n".join(examples_text))
    prompt = prompt.replace("[PAGE_WORDS_PLACEHOLDER]", page_words_text)

    return prompt


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python build_prompt.py <path_to_indexed_words.txt>")
        print("Example: python build_prompt.py scripts/llm_examples/page_010_input.txt")
        sys.exit(1)

    target_words = Path(sys.argv[1]).read_text(encoding="utf-8")
    prompt = build_prompt_for_page(target_words)

    out_path = Path("scripts/llm_prompt_ready.txt")
    out_path.write_text(prompt, encoding="utf-8")
    print(f"Prompt saved to {out_path}")
    print(f"Total prompt length: {len(prompt)} characters")
