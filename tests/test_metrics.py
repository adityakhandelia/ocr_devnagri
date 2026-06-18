"""Tests for metrics calculation module."""

import pytest
from src.utils.metrics import calculate_wer_cer, get_error_details


def test_calculate_wer_cer_perfect_match():
    """Test WER/CER calculation with identical strings."""
    reference = "नमस्ते दुनिया"
    hypothesis = "नमस्ते दुनिया"

    wer, cer = calculate_wer_cer(reference, hypothesis)

    assert wer == 0.0
    assert cer == 0.0


def test_calculate_wer_cer_with_errors():
    """Test WER/CER calculation with errors."""
    reference = "नमस्ते दुनिया"
    hypothesis = "नमस्ते dunia"  # Mixed script error

    wer, cer = calculate_wer_cer(reference, hypothesis)

    assert wer > 0.0
    assert cer > 0.0


def test_calculate_wer_cer_empty_reference():
    """Test WER/CER calculation with empty reference."""
    reference = ""
    hypothesis = "नमस्ते"

    wer, cer = calculate_wer_cer(reference, hypothesis)

    assert wer == 0.0
    assert cer == 0.0


def test_get_error_details_returns_all_fields():
    """Test that get_error_details returns all expected fields."""
    reference = "नमस्ते दुनिया"
    hypothesis = "नमस्ते दुनिया"

    details = get_error_details(reference, hypothesis)

    assert "wer" in details
    assert "cer" in details
    assert "word_accuracy" in details
    assert "char_accuracy" in details
    assert "ref_word_count" in details
    assert "hyp_word_count" in details
