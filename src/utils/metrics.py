"""Metrics calculation for OCR evaluation.

This module provides functions to calculate Word Error Rate (WER) and
Character Error Rate (CER) between reference and hypothesis texts.
"""

import jiwer
from typing import Tuple


def calculate_wer_cer(reference: str, hypothesis: str) -> Tuple[float, float]:
    """Calculate Word Error Rate and Character Error Rate.

    Args:
        reference: Ground truth text (correct transcription).
        hypothesis: OCR output or predicted text.

    Returns:
        Tuple of (WER, CER) as floats between 0.0 and 1.0+.
        Returns (0.0, 0.0) if reference is empty.
    """
    # Clean inputs
    ref = reference.strip()
    hyp = hypothesis.strip()

    if not ref:
        return 0.0, 0.0

    # Calculate WER
    wer = jiwer.wer(ref, hyp)

    # Calculate CER
    cer = jiwer.cer(ref, hyp)

    return float(wer), float(cer)


def calculate_word_accuracy(reference: str, hypothesis: str) -> float:
    """Calculate word-level accuracy (1 - WER).

    Args:
        reference: Ground truth text.
        hypothesis: Predicted text.

    Returns:
        Word accuracy as a float between 0.0 and 1.0.
    """
    wer, _ = calculate_wer_cer(reference, hypothesis)
    return max(0.0, 1.0 - wer)


def calculate_character_accuracy(reference: str, hypothesis: str) -> float:
    """Calculate character-level accuracy (1 - CER).

    Args:
        reference: Ground truth text.
        hypothesis: Predicted text.

    Returns:
        Character accuracy as a float between 0.0 and 1.0.
    """
    _, cer = calculate_wer_cer(reference, hypothesis)
    return max(0.0, 1.0 - cer)


def get_error_details(reference: str, hypothesis: str) -> dict:
    """Get detailed error analysis.

    Args:
        reference: Ground truth text.
        hypothesis: Predicted text.

    Returns:
        Dictionary containing:
        - wer: Word Error Rate
        - cer: Character Error Rate
        - word_accuracy: Word-level accuracy
        - char_accuracy: Character-level accuracy
        - ref_word_count: Number of words in reference
        - hyp_word_count: Number of words in hypothesis
        - ref_char_count: Number of characters in reference
        - hyp_char_count: Number of characters in hypothesis
    """
    wer, cer = calculate_wer_cer(reference, hypothesis)

    ref_words = len(reference.split())
    hyp_words = len(hypothesis.split())
    ref_chars = len(reference)
    hyp_chars = len(hypothesis)

    return {
        "wer": round(wer, 4),
        "cer": round(cer, 4),
        "word_accuracy": round(max(0.0, 1.0 - wer), 4),
        "char_accuracy": round(max(0.0, 1.0 - cer), 4),
        "ref_word_count": ref_words,
        "hyp_word_count": hyp_words,
        "ref_char_count": ref_chars,
        "hyp_char_count": hyp_chars,
    }
