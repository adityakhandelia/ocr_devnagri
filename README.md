# Devanagari Legislative Debates Archive

A complete pipeline to digitize historical Devanagari (Hindi) parliamentary documents and publish them as a searchable, readable web archive.

**Live demo**: https://adityakhandelia.github.io/ocr_devnagri

> 📋 **For development agents:** See [`AGENTS.md`](AGENTS.md) for coding constraints, execution logs, and module implementation status.

## What it does

1. **Ingest** — Converts PDF pages to 300 DPI PNG images.
2. **OCR** — Extracts Devanagari text using Google Gemini Flash via OpenRouter.
3. **Parse** — Structures raw OCR into speaker-attributed debate transcripts.
4. **Track** — Persists progress, paths, tokens, and cost in SQLite.
5. **Publish** — Serves a React + Tailwind web UI on GitHub Pages.

## Features

- 📄 **PDF to images** at 300 DPI via PyMuPDF
- 🤖 **Devanagari OCR** via OpenRouter (`~google/gemini-flash-latest`)
- 🗣️ **Speaker parsing** for parliamentary transcripts
- 📊 **Pipeline tracking** in SQLite (`data/pipeline.db`)
- 💰 **Token usage & cost** tracking
- 📈 **WER/CER metrics** using jiwer
- 🌐 **React frontend** with Hansard-style dashboard UI
- 🚀 **One-click GitHub Pages deployment** via GitHub Actions

## Project Structure

```
ocr_devnagri/
├── .github/workflows/deploy.yml   # GitHub Pages deployment
├── frontend/                       # React + Vite + Tailwind web UI
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── StatsCards.tsx
│   │   │   ├── PageNavigation.tsx
│   │   │   └── SpeechView.tsx
│   │   └── hooks/useDebateData.ts
│   ├── public/data/debates.json   # Structured debate data
│   └── package.json
├── scripts/
│   ├── full_pdf_pipeline.py       # Full pipeline: PDF → images → OCR → JSON
│   ├── parse_debates.py           # OCR text → structured JSON
│   ├── generate_frontend_json.py  # JSON generation without OCR
│   ├── init_tracker.py            # Initialize SQLite tracker
│   └── check_tracker.py           # Check pipeline progress
├── src/
│   ├── app.py                     # Flask annotation UI (legacy)
│   ├── database/
│   │   ├── schema.py              # Annotation database schema
│   │   └── pipeline_tracker.py    # Pipeline tracking SQLite layer
│   └── utils/
│       ├── pdf_converter.py       # PDF → image conversion
│       ├── ocr_engine.py          # OpenRouter Gemini wrapper
│       ├── transliteration.py     # Google IME transliteration
│       └── metrics.py             # WER/CER calculation
├── data/
│   ├── full_pdf_images/           # Generated page images
│   ├── full_pdf_ocr/              # Generated OCR text
│   └── pipeline.db                # Pipeline SQLite database
├── ceDscX/                        # Source PDFs (not tracked in git)
├── pyproject.toml                 # Python dependencies
└── README.md
```

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 20+ (for frontend)
- OpenRouter API key

### 1. Clone and setup Python environment

```bash
git clone https://github.com/adityakhandelia/ocr_devnagri.git
cd ocr_devnagri
uv sync
```

### 2. Configure OpenRouter API key

```bash
cp .env.example .env
# Edit .env and add:
# OPENROUTER_API_KEY=sk-or-v1-...
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Usage

### Full pipeline (PDF → images → OCR → JSON)

Place your PDF in `ceDscX/` (or update `PDF_PATH` in `scripts/full_pdf_pipeline.py`), then run:

```bash
uv run python scripts/full_pdf_pipeline.py
```

This will:
1. Convert the PDF to images in `data/full_pdf_images/<pdf_name>/`
2. Run OCR on each page and save text to `data/full_pdf_ocr/<pdf_name>/`
3. Update `data/pipeline.db` with status, tokens, and cost
4. Generate `frontend/public/data/debates.json`

### Generate frontend JSON only (no API calls)

If you already have OCR text files:

```bash
uv run python scripts/generate_frontend_json.py
```

### Check pipeline progress

```bash
uv run python scripts/check_tracker.py
```

## Frontend Development

```bash
cd frontend
npm run dev
```

Open http://localhost:5173

### Build for production

```bash
npm run build
```

Output is in `frontend/dist/`.

## Deployment to GitHub Pages

Deployment is handled automatically by GitHub Actions (`.github/workflows/deploy.yml`).

### Steps

1. Push the repo to GitHub.
2. Go to **Settings → Pages** in your GitHub repo.
3. Under **Build and deployment**, select **GitHub Actions**.
4. Every push to `main` will build and deploy the frontend.

The live site will be at:

```
https://adityakhandelia.github.io/ocr_devnagri
```

> The `base` path in `frontend/vite.config.ts` and the `homepage` field in `frontend/package.json` are already configured for the repo name `ocr_devnagri`. If you rename the repo, update both values.

## Cost Estimation

OpenRouter charges approximately **$9 per 1M tokens** for Gemini Flash.

- Average cost per page: ~$0.04
- A typical 88-page volume: ~$3.50–$4.00

Actual cost is tracked in `data/pipeline.db` after each OCR run.

## Pipeline Database Schema

The SQLite database (`data/pipeline.db`) tracks:

| Column | Description |
|--------|-------------|
| `pdf_name` | Source PDF filename |
| `pdf_path` | Path to source PDF |
| `page_number` | Page index |
| `image_path` | Path to generated PNG |
| `ocr_text_path` | Path to OCR text file |
| `ocr_status` | pending / processing / done / failed |
| `prompt_tokens` | Input tokens used |
| `completion_tokens` | Output tokens used |
| `total_tokens` | Total tokens used |
| `estimated_cost` | Estimated API cost in USD |

## Troubleshooting

### 402 Error: Insufficient Credits

Your OpenRouter account needs more credits. Add credits at https://openrouter.ai/credits.

### 408 Error while pushing to GitHub

The repo contains large generated files (PDFs, images). Make sure these are in `.gitignore`:

```gitignore
ceDscX/
*.pdf
data/full_pdf_images/
data/full_pdf_ocr/
data/sampled_images/
data/ground_truth_texts/
data/pipeline.db
frontend/node_modules/
frontend/dist/
```

If already committed, remove them from history:

```bash
git rm -r --cached data/full_pdf_images data/full_pdf_ocr ceDscX
rm -rf frontend/.git
git commit --amend -m "Initial commit"
git push -u origin main --force
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License

## Acknowledgments

- Google Gemini for multimodal OCR
- OpenRouter for API gateway access
- Google Input Tools for transliteration
- PyMuPDF for PDF conversion
- Tailwind CSS and Vite for the frontend
