# LLM-Based Transcript Parsing Pipeline

This pipeline converts raw OCR text into a structured JSON format using word-level indexing and an LLM.

## Pipeline Overview

```
OCR text file
    ↓
Index words (scripts/index_ocr_page.py)
    ↓
Build LLM prompt with examples (scripts/llm_parser.py)
    ↓
Call LLM (scripts/llm_parser.py)
    ↓
Parse LLM output index ranges
    ↓
Reconstruct text segments (scripts/llm_parser.py)
    ↓
Save per-page JSON + final debates JSON
```

## Files

| File | Purpose |
|------|---------|
| `scripts/index_ocr_page.py` | Convert OCR text to indexed word list |
| `scripts/llm_parser.py` | Build prompt, call LLM, parse and validate output, reconstruct segments |
| `scripts/run_llm_pipeline.py` | End-to-end pipeline for all pages |
| `scripts/generate_manual_marking_page.py` | Generate a blank indexed word list for manual marking |
| `scripts/manual_marking_template.json` | Template for manual marking output |
| `scripts/llm_examples/page_009_input.txt` | Example indexed page 9 |
| `scripts/llm_examples/page_009_output.json` | Example LLM output for page 9 |
| `scripts/page_010_for_manual_marking.txt` | Blank indexed page 10 for you to mark |

## Step 1: Add Examples (Manual Marking)

Before running the pipeline, you need at least one manually marked example.

### Option A: Mark page 10 yourself

1. Open `scripts/page_010_for_manual_marking.txt`
2. Read the indexed words
3. Fill `scripts/manual_marking_template.json` with correct ranges
4. Save it as `scripts/llm_examples/page_010_output.json`
5. Copy `scripts/page_010_for_manual_marking.txt` to `scripts/llm_examples/page_010_input.txt`

### Option B: Use the already-marked page 9

Page 9 is already in `scripts/llm_examples/`:
- `page_009_input.txt`
- `page_009_output.json`

## Step 2: Run the Pipeline

Parse a single page:

```bash
uv run python scripts/run_llm_pipeline.py --page 10
```

Parse all pages:

```bash
uv run python scripts/run_llm_pipeline.py
```

Parse only first 5 pages for testing:

```bash
uv run python scripts/run_llm_pipeline.py --limit 5
```

## Step 3: Output

- Per-page JSON: `data/llm_parsed/page_XXX.json`
- Final UI JSON: `frontend/public/data/debates_llm.json`

## Step 4: Use in UI

Update `frontend/src/hooks/useDebateData.ts` to load the new JSON:

```ts
fetch(`${import.meta.env.BASE_URL}data/debates_llm.json`)
```

Then rebuild and deploy.

## LLM Output Format

The LLM returns only index ranges:

```json
{
  "page_number": 10,
  "total_words": 402,
  "metadata": [[0, 7]],
  "headings": [[8, 15]],
  "announcements": [{"range": [16, 40], "subtype": "chair"}],
  "speeches": [{"range": [41, 80], "speaker_range": [41, 44]}],
  "member_lists": [],
  "narrative": []
}
```

## LLM Model

Default model is `deepseek/deepseek-v4-flash` via OpenRouter. It is fast, cheap, and handles Hindi well.

To use a different model:

```bash
uv run python scripts/run_llm_pipeline.py --model deepseek/deepseek-chat
```

Or set in `.env`:

```bash
LLM_MODEL=deepseek/deepseek-v4-flash
```

## Notes

- Output tokens are small (~50 per page), so API cost is low.
- The pipeline validates coverage and overlap automatically.
- Add more examples for better accuracy on edge cases.
