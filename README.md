# Devanagari OCR & Annotation Platform

A robust, local web-based correction and metrics platform for Devanagari text digitization using Gemini via OpenRouter for first-draft OCR, real-time transliteration support, and WER/CER tracking.

> 📋 **For development agents:** See [`AGENTS.md`](AGENTS.md) for coding constraints, execution logs, and module implementation status.

## Features

- **High-precision OCR**: Uses Google Gemini 1.5 Flash for accurate Devanagari text extraction
- **Real-time Transliteration**: Phonetic English-to-Devanagari typing with Google IME API
- **Metrics Tracking**: Automatic WER (Word Error Rate) and CER (Character Error Rate) calculation
- **SQLite Database**: Transactional storage for ground truth data and annotation progress
- **Web Interface**: Flask-based web UI for efficient text correction

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/) (fast Python package installer)
- OpenRouter API key (get it from [OpenRouter](https://openrouter.ai/keys))

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ocr-devnagri
```

2. Install dependencies with uv (this reads pyproject.toml and installs everything):
```bash
uv sync
```

3. Configure your OpenRouter API key:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-...
```

> **Note:** This project uses OpenRouter as a unified API gateway to access Gemini models. OpenRouter provides a single API key that works with multiple providers (Google, OpenAI, Anthropic, etc.).

## Usage

### 1. Initialize Dataset from PDFs

Place your PDF files in a directory (e.g., `ceDscX/` or `data/raw/`), then initialize the dataset:

```bash
# Auto-detect PDF directory (checks ceDscX/, then data/raw/)
uv run python init_dataset.py

# Or specify a custom directory
uv run python init_dataset.py path/to/pdf/folder

# With OCR generation (requires Gemini API key in .env)
uv run python init_dataset.py --with-ocr
uv run python init_dataset.py ceDscX/ --with-ocr
```

**What this does:**
- Converts each PDF page to 300 DPI PNG images in `data/images/`
- Creates database records for each page in `data/annotations.db`
- (Optionally) Generates OCR drafts using Gemini 1.5 Flash API

### 2. Run the Application

```bash
uv run python -m src.app
```

The web interface will be available at **`http://localhost:5000`** (or next available port 5000-5009)

You should now see images loaded in the UI for annotation.

### 3. Workflow

1. **Prepare**: Place PDFs in any directory
2. **Initialize**: Run `init_dataset.py` to convert and load into database
3. **View**: Open the web UI to see images and OCR drafts
4. **Correct**: Edit the OCR text to create ground truth annotations
5. **Track**: Metrics (WER/CER) are automatically calculated and saved

### 4. Batch Processing

For custom batch processing:

```python
from src.utils.pdf_converter import convert_pdf_to_images
from src.utils.ocr_engine import get_gemini_ocr
from src.database.schema import init_db, insert_page, save_ocr_draft

# Initialize database
init_db()

# Process PDFs
pdf_path = "ceDscX/1952_1_100_2.pdf"
image_paths = convert_pdf_to_images(pdf_path, "data/images/")

# Extract OCR for each page
for i, img_path in enumerate(image_paths):
    page_id = f"doc_page_{i+1}"
    insert_page(db_path, page_id, pdf_path, i+1, img_path)
    
    ocr_text = get_gemini_ocr(img_path, api_key)
    save_ocr_draft(db_path, page_id, ocr_text)
```

## Troubleshooting

### 402 Error: Insufficient Credits

If you see an error like:
```
OpenRouter API error: 402 - This request requires more credits
```

This means your OpenRouter API key doesn't have enough credits for the request. The code now limits `max_tokens` to 4096 to minimize credit usage. Solutions:
1. Add credits to your OpenRouter account at https://openrouter.ai/credits
2. Use the free tier model (already set as default: `google/gemini-2.0-flash-exp:free`)
3. Reduce image size before processing

## Project Structure

```
ocr_devnagri/
├── AGENTS.md                   # Agent execution log & constraints
├── src/
│   ├── app.py                  # Main Flask web UI
│   ├── database/
│   │   └── schema.py           # SQLite database management
│   └── utils/
│       ├── pdf_converter.py    # PDF to image conversion
│       ├── ocr_engine.py       # OpenRouter Gemini API wrapper
│       ├── transliteration.py  # Google IME API
│       └── metrics.py          # WER/CER calculation
├── tests/                      # Unit tests
├── docs/                       # Documentation
│   ├── OCR_SPEC.md             # OCR pipeline specifications
│   ├── DATASET.md              # Dataset structure and guidelines
│   └── MODEL.md                # Model evaluation and benchmarks
├── data/                       # Data storage
│   ├── images/                 # Converted PNG images
│   └── raw/                    # Source PDFs
└── pyproject.toml              # Project configuration
```

## Database Schema

The SQLite database (`data/annotations.db`) stores:

- `page_id`: Unique identifier for each page
- `pdf_source`: Source PDF file path
- `page_number`: Page number within PDF
- `image_path`: Path to high-res PNG
- `ocr_draft`: Initial OCR output from Gemini
- `ground_truth`: Human-corrected text
- `status`: Annotation status (pending/completed/flagged)
- `wer`/`cer`: Error rates
- `annotation_time_sec`: Time spent annotating

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Google Gemini API for multimodal OCR capabilities
- Google Input Tools for transliteration support
- Gradio team for the excellent web interface framework
