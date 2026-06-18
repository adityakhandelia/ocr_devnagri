"""OCR engine using Google Gemini API via OpenRouter.

This module provides functions to extract Devanagari text from images using
the Gemini model through OpenRouter API gateway.
"""

import os
import base64
from pathlib import Path
from typing import Optional, Union
import requests
from PIL import Image


def _is_truncated(text: str) -> bool:
    """Check if text appears to be truncated (incomplete).
    
    Returns True if the text ends with an incomplete word, open parenthesis,
    hyphen, or other indicators that the model was cut off.
    """
    if not text:
        return False
    
    # Strip trailing whitespace
    text = text.rstrip()
    
    # Check for incomplete endings
    incomplete_indicators = [
        "(",       # Open parenthesis
        "-",       # Trailing hyphen (word break)
        "—",       # Em-dash
        "–",       # En-dash
        ",",       # Trailing comma (might be incomplete)
        "।",       # Hindi danda (sentence might continue)
        ":",       # Trailing colon
        ";",       # Trailing semicolon
        "\"",      # Open quote
        "'",       # Open apostrophe
        "«",       # Open guillemet
        "‹",       # Open single guillemet
        "[",       # Open bracket
        "{",       # Open brace
        "▪",       # Bullet point
        "•",       # Bullet
        "*",       # Asterisk
    ]
    
    # If text ends with any incomplete indicator
    if any(text.endswith(indicator) for indicator in incomplete_indicators):
        return True
    
    # If text ends mid-word (no space or punctuation in last 20 chars)
    last_segment = text[-20:] if len(text) >= 20 else text
    if last_segment and not any(c in last_segment for c in " \n।.,!?;:"):
        return True
    
    # Check if the text ends abruptly without a sentence-ending punctuation
    # For Hindi: check if last 50 chars don't contain a sentence ending
    last_chunk = text[-50:] if len(text) >= 50 else text
    # Hindi sentence endings: ।, ?, !, newline
    if not any(c in last_chunk for c in "।?!\n"):
        return True
    
    return False


def _continue_text(
    text: str, api_key: str, model_name: str, headers: dict, max_tokens: int
) -> tuple:
    """Send a continuation request to complete truncated text.
    
    Returns:
        Tuple of (continued_text, continuation_tokens_used)
    """
    # Get last 100 chars as context
    context = text[-100:] if len(text) >= 100 else text
    
    continuation_prompt = (
        "Continue the Devanagari transcription from EXACTLY where it left off. "
        "Do NOT repeat any text that was already transcribed. "
        "Output ONLY the continuation text, starting from the next word.\n\n"
        f"Previous text ended with: ...{context}\n\n"
        "Continue from here:"
    )
    
    payload = {
        "model": model_name,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": continuation_prompt,
                    }
                ],
            }
        ],
    }
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
    )
    
    if response.status_code != 200:
        # If continuation fails, return original text
        return text, 0
    
    result = response.json()
    continuation = result["choices"][0]["message"]["content"].strip()
    
    # Get token usage from continuation
    usage = result.get("usage", {})
    continuation_tokens = usage.get("completion_tokens", 0)
    if continuation_tokens == 0:
        # Estimate if not provided
        continuation_tokens = len(continuation) // 2
    
    # Remove any repeated text at the beginning
    # Try to find overlap and remove it
    combined_text = text + continuation
    
    return combined_text, continuation_tokens


def _handle_truncation(
    text: str, api_key: str, model_name: str, headers: dict, max_tokens: int
) -> tuple:
    """Handle truncated text by requesting continuation.
    
    Returns:
        Tuple of (full_text, total_continuation_tokens)
    """
    full_text = text
    total_continuation_tokens = 0
    max_attempts = 3
    
    for attempt in range(max_attempts):
        if not _is_truncated(full_text):
            break
        
        print(f"  Text appears truncated (attempt {attempt + 1}/{max_attempts}). Requesting continuation...")
        
        continuation, tokens = _continue_text(
            full_text, api_key, model_name, headers, max_tokens
        )
        
        total_continuation_tokens += tokens
        
        # Check if continuation actually added new content
        if len(continuation) <= len(full_text):
            break
            
        full_text = continuation
    
    return full_text, total_continuation_tokens


def get_gemini_ocr(
    image_path: Union[str, Path],
    api_key: Optional[str] = None,
    model_name: str = "~google/gemini-flash-latest",
) -> dict:
    """Extract Devanagari text from an image using Gemini via OpenRouter.

    Args:
        image_path: Path to the image file.
        api_key: OpenRouter API key. If None, reads from OPENROUTER_API_KEY env var.
        model_name: Model to use (default: ~google/gemini-flash-latest).

    Returns:
        Dictionary containing:
        - text: Extracted text from the image
        - prompt_tokens: Number of prompt tokens used
        - completion_tokens: Number of completion tokens used
        - total_tokens: Total tokens used
        - estimated_cost: Estimated cost in USD
        - model_name: Model name used

    Raises:
        ValueError: If API key is not provided or found in environment.
        FileNotFoundError: If the image file does not exist.
    """
    # Get API key
    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError(
            "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable "
            "or pass api_key parameter."
        )

    # Check if image exists
    image_path_obj = Path(image_path) if isinstance(image_path, str) else image_path
    if not image_path_obj.exists():
        raise FileNotFoundError(f"Image file not found: {image_path_obj}")

    # Optimize image size for API - resize if too large while maintaining readability
    img = Image.open(image_path_obj)
    max_dimension = 2000  # Max width or height in pixels
    if max(img.width, img.height) > max_dimension:
        ratio = max_dimension / max(img.width, img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Convert to RGB if necessary (for PNG with alpha or other modes)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Save optimized image to bytes
    import io
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG', quality=90, optimize=True)
    image_data = base64.standard_b64encode(img_buffer.getvalue()).decode("utf-8")
    
    # Use jpeg media type since we converted to RGB
    media_type = "image/jpeg"

    # Image is now optimized and converted to JPEG above
    # media_type is already set to "image/jpeg"

    # Create OCR prompt - optimized for complete page transcription
    prompt = (
        "You are an expert Devanagari OCR engine. Your task is to transcribe the COMPLETE text "
        "from the provided image. You must read and output EVERY SINGLE WORD on the page.\n\n"
        "CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:\n"
        "1. Transcribe the ENTIRE page from top to bottom, left to right\n"
        "2. Do NOT stop early - continue until you have read every last word on the page\n"
        "3. Do NOT summarize, condense, or skip any sections\n"
        "4. If the page has multiple sections, headings, or speeches, transcribe ALL of them completely\n"
        "5. Maintain exact formatting, line breaks, and paragraph structures\n"
        "6. Do not translate, explain, or interpret - output verbatim text only\n"
        "7. Retain all historical punctuation, signs, and ligatures exactly as written\n"
        "8. If a specific portion is completely unreadable, use '[unreadable]'\n"
        "9. This is a legislative document page. Continue reading through ALL paragraphs, ALL speeches, and ALL sections\n"
        "10. NEVER stop after the first paragraph or section - the page likely contains multiple speeches\n\n"
        "FAILURE MODE: If you stop early, the transcription will be incomplete and useless. "
        "You must read the entire page to the very end."
    )

    # Call OpenRouter API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "max_tokens": 8192,  # Gemini Flash max output; fits within credit limit
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}",
                        },
                    },
                ],
            }
        ],
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
    )

    if response.status_code != 200:
        raise ValueError(
            f"OpenRouter API error: {response.status_code} - {response.text}"
        )

    result = response.json()
    text = result["choices"][0]["message"]["content"].strip()
    
    # Extract token usage from response
    usage = result.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    
    # If OpenRouter doesn't provide usage, estimate
    if total_tokens == 0:
        # Estimate: ~4 chars per token for English, ~1-2 for Devanagari
        # Image tokens: ~258 tokens per 512x512 tile for Gemini
        prompt_text_length = len(prompt)
        image_width, image_height = img.size
        # Estimate image tokens (Gemini uses 258 tokens per 512x512 tile)
        tiles_x = (image_width + 511) // 512
        tiles_y = (image_height + 511) // 512
        estimated_image_tokens = tiles_x * tiles_y * 258
        estimated_prompt_tokens = (prompt_text_length // 3) + estimated_image_tokens
        estimated_completion_tokens = len(text) // 2
        prompt_tokens = estimated_prompt_tokens
        completion_tokens = estimated_completion_tokens
        total_tokens = estimated_prompt_tokens + estimated_completion_tokens
    
    # Calculate cost based on OpenRouter pricing for Gemini Flash
    # Note: OpenRouter charges significantly more than direct Google API
    # Using $9 per 1M tokens for both input and output (verified from usage)
    input_cost = (prompt_tokens / 1_000_000) * 9.0
    output_cost = (completion_tokens / 1_000_000) * 9.0
    estimated_cost = round(input_cost + output_cost, 8)
    
    return {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost": estimated_cost,
        "model_name": model_name,
    }


def batch_ocr(
    image_paths: list,
    api_key: Optional[str] = None,
    model_name: str = "~google/gemini-flash-latest",
    progress_callback: Optional[callable] = None,
) -> dict:
    """Process multiple images with OCR.

    Args:
        image_paths: List of paths to image files.
        api_key: OpenRouter API key.
        model_name: Model to use.
        progress_callback: Optional callback function(current, total) for progress updates.

    Returns:
        Dictionary mapping image paths to extracted text.
    """
    results = {}
    total = len(image_paths)

    for i, image_path in enumerate(image_paths):
        try:
            ocr_result = get_gemini_ocr(image_path, api_key, model_name)
            results[image_path] = ocr_result["text"]
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            results[image_path] = ""

        if progress_callback:
            progress_callback(i + 1, total)

    return results
