# OCR Specification Document

## Overview

This document details the technical specifications for the Devanagari OCR pipeline, including model configuration, prompt engineering, and output formatting.

> For agent constraints and execution logs, see [`AGENTS.md`](../AGENTS.md) in the project root.

## Model Configuration

### Primary Model: Gemini 1.5 Flash

**Model ID:** `gemini-1.5-flash`

**Parameters:**
- Temperature: 0.0 (deterministic output)
- Max tokens: 4096
- Top-p: 0.95
- Top-k: 1

**Reasoning:**
- Optimized for fast, low-latency inference
- Excellent multimodal vision capabilities for document understanding
- Superior handling of complex Devanagari ligatures and historical fonts

## Prompt Engineering

### System Prompt

```
You are an expert Devanagari OCR engine with specialized training in:
- Historical and modern Devanagari scripts
- Complex ligatures (संयुक्ताक्षर) and conjuncts
- Sanskrit, Hindi, and Marathi text conventions
- Document layout preservation

Transcription Rules:
1. EXACT TRANSCRIPTION: Output text exactly as written in the image
2. PRESERVE FORMATTING: Maintain line breaks, paragraph structures, and spacing
3. NO TRANSLATION: Do not translate or interpret the content
4. RETAIN LIGATURES: Keep all conjuncts and complex characters intact
5. PUNCTUATION: Preserve all punctuation marks, symbols, and diacritics
6. UNREADABLE: Use [unreadable] for illegible sections
7. WHITESPACE: Preserve leading/trailing spaces if they indicate structure

Output Format:
- Plain text only
- UTF-8 encoded
- No markdown or HTML
- Line breaks preserved with \n
```

## Image Processing

### Preprocessing Pipeline

1. **Resolution Enhancement**
   - Target DPI: 300
   - Color mode: Grayscale conversion
   - Format: PNG (lossless)

2. **Quality Checks**
   - Minimum resolution: 2000x3000 pixels
   - Contrast verification
   - Skew detection (flag pages >5° rotation)

3. **Batch Processing**
   - Parallel processing capability
   - Memory-efficient streaming
   - Progress tracking per document

## Output Format

### Raw OCR Output Structure

```json
{
  "page_id": "doc_page_001",
  "raw_text": "Transcribed text here...",
  "confidence": 0.95,
  "processing_time_ms": 2345,
  "warnings": ["low_contrast_region_detected"]
}
```

### Text Encoding

- **Encoding:** UTF-8
- **Normalization:** NFC (Canonical Decomposition followed by Canonical Composition)
- **Line Endings:** Unix-style (\n)

## Error Handling

### Retry Strategy

1. **Transient Errors:**
   - Rate limiting: Exponential backoff (1s, 2s, 4s, 8s)
   - Network timeout: Retry up to 3 times
   - Partial content: Request retry

2. **Permanent Errors:**
   - Invalid API key: Halt processing
   - Corrupted image: Log and skip
   - Unsupported format: Convert or skip

## Performance Metrics

### Expected Accuracy

- **Clean modern text:** >95% character accuracy
- **Historical documents:** >85% character accuracy
- **Degraded/aged:** >70% character accuracy (flag for manual review)

### Latency Targets

- **Single page:** <5 seconds average
- **Batch (100 pages):** <8 minutes total
- **Web UI load:** Instant (pre-computed)

## Quality Assurance

### Automated Checks

1. **Character Set Validation**
   - Verify all characters in Devanagari Unicode block
   - Flag suspicious characters or encoding issues

2. **Structure Validation**
   - Detect missing line breaks
   - Identify potential column confusion
   - Flag unusual character sequences

3. **Length Consistency**
   - Compare output length to image dimensions
   - Flag extremely short/long outputs

## Integration Points

### Database Storage

- Store raw OCR in `page_annotations.ocr_draft`
- Link to source image via `image_path`
- Track processing timestamp

### Metrics Calculation

- Compare against ground truth for WER/CER
- Store error rates for model evaluation
- Track improvement over time

## Future Enhancements

1. **Multi-Model Ensemble**
   - Combine Gemini with local PaddleOCR
   - Confidence-weighted voting

2. **Layout Analysis**
   - Automatic table detection
   - Multi-column handling
   - Header/footer removal

3. **Active Learning**
   - Flag low-confidence outputs
   - Prioritize for human review
   - Retrain on corrected data
