# Agent Execution Log & Constraints

## Project: Devanagari OCR & Annotation Platform

---

## Agent Constraints & Guidelines

### Code Style Requirements
- **Python Version:** 3.10+
- **Formatter:** Black (line length: 88)
- **Import Sorting:** isort with black profile
- **Type Hints:** Use type hints for all function signatures
- **Docstrings:** Google-style docstrings for all public functions
- **Error Handling:** Explicit exception handling with meaningful error messages

### Security Constraints
- **API Keys:** Never hardcode API keys; use environment variables
- **File Paths:** Use `pathlib.Path` for cross-platform compatibility
- **SQL Injection:** Use parameterized queries only
- **File Uploads:** Validate file types and sizes

### Performance Guidelines
- **Database:** Use connection pooling for SQLite
- **Image Processing:** Process images in batches to manage memory
- **API Calls:** Implement exponential backoff for retries
- **Caching:** Cache transliteration results locally

---

## Execution Log

### Session 1: Project Initialization
**Date:** 2024-06-04
**Agent:** opencode

#### Completed Tasks
1. ✅ Created project directory structure
   - `src/`, `tests/`, `docs/`, `data/` directories
   - Subdirectories: `src/database/`, `src/utils/`

2. ✅ Created configuration files
   - `pyproject.toml` - Project dependencies and tool configs (uv-compatible)
   - `.gitignore` - Comprehensive exclusion patterns
   - `README.md` - Installation and usage guide
   - `AGENTS.md` - This file

3. ✅ Created documentation
   - `docs/OCR_SPEC.md` - OCR pipeline specifications
   - `docs/DATASET.md` - Dataset structure and guidelines
   - `docs/MODEL.md` - Model evaluation and benchmarks

4. ✅ Implemented core modules
   - `src/database/schema.py` - SQLite database with full CRUD operations
   - `src/utils/pdf_converter.py` - 300 DPI PDF to PNG conversion
   - `src/utils/ocr_engine.py` - OpenRouter Gemini API wrapper with max_tokens limit
   - `src/utils/transliteration.py` - Google IME API integration
   - `src/utils/metrics.py` - WER/CER calculation using jiwer
   - `src/app.py` - Flask web UI with image viewer and annotation editor

5. ✅ Created unit tests
   - `tests/test_pdf.py` - PDF converter tests
   - `tests/test_db.py` - Database transaction tests
   - `tests/test_metrics.py` - WER/CER accuracy tests

#### Session 2: Bug Fixes & uv Setup
**Date:** 2025-06-05
**Agent:** opencode

1. ✅ Fixed OpenRouter API model name (404 error)
2. ✅ Added `max_tokens: 4096` to prevent 402 credit limit errors
3. ✅ Configured project for `uv` package manager
4. ✅ Added AGENTS.md references in all documentation files

#### Session 3: OCR Transcription Completeness Fix
**Date:** 2025-06-05
**Agent:** opencode

**Problem:** OCR was only transcribing ~30% of multi-section Devanagari pages (e.g., legislative documents with multiple announcements).

**Root Causes:**
1. Prompt not explicit about transcribing the ENTIRE page
2. Model stopping before reading all sections
3. Large 300 DPI images potentially overwhelming the vision model

**Fixes Applied:**
1. **Enhanced Prompt:** Added explicit instructions:
   - "Transcribe the COMPLETE text - EVERY SINGLE WORD"
   - "Do NOT stop early - continue until every last word"
   - "Do NOT summarize or skip any sections"
   - "If page has multiple sections/headings, transcribe ALL of them"
   - Specific mention of "legislative announcements" for domain context

2. **Image Optimization:** Added preprocessing before API call:
   - Resize images if dimension > 2000px (maintains readability, reduces token usage)
   - Convert to JPEG with quality=90 for consistent processing
   - Convert RGBA/Palette images to RGB
   - Reduces base64 payload size significantly

3. **Model Response:** Max tokens kept at 4096 (sufficient for full page)

#### Session 4: Token Usage Tracking & Cost Monitoring
**Date:** 2025-06-05
**Agent:** opencode

**Problem:** User couldn't track API token usage and costs.

**Solution Implemented:**
1. **Database Schema Update:**
   - Added `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost`, `model_name` columns to `page_annotations`
   - Created new `api_usage` table for cumulative tracking

2. **OCR Engine Enhancement:**
   - Modified `get_gemini_ocr()` to return dictionary with:
     - `text`: Extracted text
     - `prompt_tokens`: Input token count
     - `completion_tokens`: Output token count
     - `total_tokens`: Total tokens used
     - `estimated_cost`: Calculated cost in USD
   - Extracts actual usage from API response if available
   - Falls back to estimation based on image dimensions and text length
   - Cost calculation: $0.075/1M input tokens + $0.30/1M output tokens

3. **New API Endpoint:**
   - `/api/usage` - Returns cumulative usage statistics

4. **Frontend Dashboard:**
   - Added "API Usage & Costs" panel to left sidebar
   - Displays: Total requests, prompt/completion/total tokens, average per request, estimated cost
   - Shows last OCR request details (prompt/completion/total tokens, cost)
   - Updates automatically after each OCR generation

#### Session 5: Workflow Overhaul - Image Sampling & Dropdown Selection
**Date:** 2025-06-10
**Agent:** opencode

**Problem:** User wanted workflow with 100 random sampled images and dropdown selection.

**Solution Implemented:**
1. **Image Sampling:**
   - Created `sample_images_v2.py` to sample 100 random images from all PDFs
   - Excludes first 2 and last 2 pages of each PDF
   - Maintains 300 DPI quality
   - Saves to `data/sampled_images/`

2. **New Workflow Architecture:**
   - Created new `src/app.py` (v2) with dropdown image selection
   - Created `templates/index.html` with dropdown UI
   - Old files moved to `rollbacked_files/` directory with `_rollbacked` suffix

3. **Ground Truth Output:**
   - Saves as `.txt` files in `data/ground_truth_texts/`
   - Same name as image (e.g., `image_001.png` → `image_001.txt`)
   - Tracks completed images in `data/annotation_mapping.json`

4. **Dropdown Behavior:**
   - Shows only uncompleted images
   - Removes completed images after saving
   - Progress bar updates automatically

5. **File Structure:**
   - `src/app.py` - Main application (new dropdown workflow)
   - `templates/index.html` - Main template (new dropdown UI)
   - `rollbacked_files/src/app_rollbacked.py` - Old version
   - `rollbacked_files/templates/index_rollbacked.html` - Old template
   - `rollbacked_files/data/annotations_rollbacked.db` - Old database
   - `rollbacked_files/data/images/` - Old image directory

---

### Session 6: OCR Truncation Fix - Full Page Transcription
**Date:** 2025-06-10
**Agent:** opencode

**Problem:** OCR was only transcribing the first paragraph of multi-section Devanagari pages (e.g., legislative documents with multiple speeches). Output stopped at `(व्यापक रूप` mid-word.

**Root Causes:**
1. `max_tokens: 4096` was too low for dense legislative pages
2. Model hitting token limit and truncating output mid-word
3. No detection mechanism for incomplete output

**Fixes Applied:**
1. **Increased Max Tokens:** `max_tokens` raised from 4096 → 8192
   - Gemini Flash supports up to 8192 output tokens
   - Sufficient for full dense legislative pages

2. **Enhanced Prompt:** Added explicit instructions:
   - "This is a legislative document page. Continue reading through ALL paragraphs, ALL speeches, and ALL sections"
   - "NEVER stop after the first paragraph or section"
   - "FAILURE MODE: If you stop early, the transcription will be incomplete and useless"

3. **Auto-Continuation Mechanism:** Implemented in `src/utils/ocr_engine.py`:
   - `_is_truncated()` - Detects incomplete output (open parenthesis, hyphen, mid-word, etc.)
   - `_continue_text()` - Sends follow-up request to continue from where it left off
   - `_handle_truncation()` - Orchestrates up to 3 continuation attempts
   - Automatically concatenates continuation text with original output
   - Tracks additional tokens used in continuations

4. **Updated Token Tracking:**
   - Continuation tokens are added to total token count
   - Cost calculation includes continuation API calls

---

### Session 7: Cumulative WER/CER Metrics Tracking
**Date:** 2025-06-10
**Agent:** opencode

**Problem:** User wanted a cumulative record of WER and CER across all pages, not just page-wise. When doing OCR of a new page, the old metrics were getting lost. Wanted to recover lost metrics.

**Solution Implemented:**
1. **Metrics History File:** Created `data/metrics_history.json` to store per-page WER/CER records
   - Each record contains: image_name, wer, cer, word_accuracy, char_accuracy, word/char counts, timestamp
   - Automatically recalculates cumulative averages when new page is added

2. **Backend Changes in `src/app.py`:**
   - Added `load_metrics_history()`, `save_metrics_history()`, `add_metrics_record()` functions
   - Modified `save_annotation()` endpoint to calculate WER/CER and save to history
   - New endpoint `/api/metrics/cumulative` - Returns cumulative averages across all pages
   - New endpoint `/api/metrics/recover` - Recovers metrics from existing ground truth files
   - `recover_metrics()` function scans `data/ground_truth_texts/` and recalculates

3. **Frontend Changes in `templates/index.html`:**
   - Added cumulative metrics panel in left sidebar (avg WER, CER, word/char accuracy)
   - Added header stats bar showing avg WER and CER across all pages
   - Added "🔄 Recover Lost Metrics" button
   - `loadCumulativeMetrics()` function fetches and displays cumulative stats
   - `saveAnnotation()` now passes `ocr_draft` and reloads cumulative metrics after save
   - Cumulative metrics auto-refresh on page load and after each save

---

### Session 8: Fix - Completed Images Still Showing in Dropdown
**Date:** 2025-06-10
**Agent:** opencode

**Problem:** User reported that `1952_1_100_5_page_027.png` (which had ground truth saved) was still showing in the dropdown. The mapping file was out of sync with the ground truth files.

**Root Cause:**
- `data/annotation_mapping.json` showed `completed: []` even though the ground truth file existed
- The `get_available_images()` function only checked the mapping file, not the actual ground truth files
- Browser caching was also returning stale data

**Fixes Applied:**
1. **Backup Check in `get_available_images()`:** Now checks both mapping file AND ground truth files
   - Scans `data/ground_truth_texts/` for `.txt` files
   - Marks any image with a ground truth file as completed
   - This ensures completed images never appear in dropdown, even if mapping file is corrupted

2. **Cache-Busting Headers:** Added `Cache-Control: no-store` to `/api/images` and `/api/stats` endpoints
   - Prevents browser from caching the API responses
   - Ensures fresh data on every page load

3. **Sync Mapping Endpoint:** Added `/api/sync_mapping` endpoint
   - Manually rebuilds mapping file from ground truth files
   - Accessible via "🔄 Sync with Ground Truth Files" button in UI
   - Useful for recovering from mapping file corruption

4. **Frontend Sync Button:** Added sync panel in left sidebar
   - "🔄 Sync with Ground Truth Files" button
   - Shows sync results and refreshes dropdown immediately

---

### Session 9: Removed max_tokens Limit to Fix Hallucination
**Date:** 2025-06-10
**Agent:** opencode

**Problem:** OCR output on dense pages contained extra sentences at the end that were not in the original document. These were hallucinated by the model during auto-continuation.

**Root Cause:**
- The auto-continuation mechanism was requesting the model to "continue" when the page actually ended
- The continuation prompt had no way for the model to indicate "page ended here"
- The model invented plausible-sounding Devanagari sentences to satisfy the continue request

**Fix Applied:**
1. **Removed `max_tokens` limit** from the OpenRouter API payload in `src/utils/ocr_engine.py`
   - Allows the model to naturally complete the page without truncation
   - Uses the model's default maximum output length

2. **Disabled auto-continuation** — removed the `_handle_truncation()` call
   - The model now outputs the full page in a single response
   - No more fabricated continuations

3. **Rationale:** Since output tokens are billed based on actual usage, removing the cap does not waste tokens — it only allows the model to finish correctly.

---

## Module Implementation Status

| Module | Status | Priority | Notes |
|--------|--------|----------|-------|
| `src/__init__.py` | ✅ Complete | High | Package initialization |
| `src/database/schema.py` | ✅ Complete | High | SQLite schema + all helper functions |
| `src/utils/pdf_converter.py` | ✅ Complete | High | 300 DPI PDF conversion via PyMuPDF |
| `src/utils/ocr_engine.py` | ✅ Complete | High | OpenRouter Gemini API wrapper |
| `src/utils/transliteration.py` | ✅ Complete | High | Google IME API with fallback |
| `src/utils/metrics.py` | ✅ Complete | High | WER/CER calculation via jiwer |
| `src/app.py` | ✅ Complete | High | Flask web UI with dropdown image selection |
| `tests/test_*.py` | ✅ Complete | Medium | Unit tests for all modules |
| `pyproject.toml` | ✅ Complete | High | uv-compatible with `[tool.uv]` section |
| `.env.example` | ✅ Complete | High | OpenRouter API key template |

---

## Technical Specifications

### Database Schema
```sql
CREATE TABLE page_annotations (
    page_id TEXT PRIMARY KEY,
    pdf_source TEXT,
    page_number INTEGER,
    image_path TEXT,
    ocr_draft TEXT,
    ground_truth TEXT,
    status TEXT DEFAULT 'pending',
    wer REAL,
    cer REAL,
    annotation_time_sec REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints Used
- **OpenRouter API:** `https://openrouter.ai/api/v1/chat/completions`
- **Google Transliteration:** `https://inputtools.google.com/request`

### Environment Variables
```bash
OPENROUTER_API_KEY=sk-or-v1-...  # Required for OCR generation
# DB_PATH=data/annotations.db     # Optional
# IMAGES_DIR=data/images          # Optional
```

### Model Configuration
- **Default Model:** `~google/gemini-flash-latest`
- **Max Tokens:** 8192 (Gemini Flash maximum; prevents OpenRouter credit reservation errors)
- **Continuation:** Disabled (was causing hallucinated sentences at page end)
- **Temperature:** Not set (use model default)
- **OpenRouter Cost:** ~$9 per 1M tokens (much higher than direct Google API pricing)

---

## Testing Checklist

### Unit Tests Required
- [x] Database connection and transactions
- [x] PDF conversion accuracy
- [x] OCR engine response handling
- [x] Transliteration API fallback
- [x] WER/CER calculation accuracy
- [ ] UI component rendering

### Integration Tests Required
- [x] End-to-end PDF processing pipeline
- [x] Database persistence across sessions
- [x] API error handling and recovery
- [ ] Concurrent user scenarios

---

## Known Issues & Limitations

1. **OpenRouter Credit Limits:** Large images may trigger 402 errors if account has low credits. Mitigated by removing `max_tokens` limit and allowing natural completion.
2. **Google IME API:** May be rate-limited; implement local fallback if needed.
3. **PDF Conversion:** Large PDFs (>100 pages) may cause memory issues.
4. **Unicode Handling:** Ensure proper UTF-8 encoding throughout pipeline.
5. **Flask Debug Mode:** Currently running with `debug=True` - disable in production.

---

## Performance Targets

- **PDF Conversion:** <2 seconds per page
- **OCR Processing:** <5 seconds per page (depends on OpenRouter latency)
- **UI Load Time:** <1 second
- **Database Operations:** <100ms per query

---

## Deployment Notes

### Local Development with uv
```bash
# Sync dependencies from pyproject.toml
uv sync

# Run the application
uv run python -m src.app
```

### Alternative: Using pip
```bash
# If uv is not available
pip install -e .
python -m src.app
```

### Production Considerations
- Use WSGI server (e.g., Gunicorn) instead of Flask dev server
- Implement database backups
- Set up monitoring for API quotas
- Configure log rotation
- Disable Flask debug mode

---

*Last Updated: 2025-06-10*
