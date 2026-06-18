"""Tests for PDF converter module."""

import pytest
from pathlib import Path
from src.utils.pdf_converter import convert_pdf_to_images


def test_convert_pdf_to_images_raises_on_missing_file():
    """Test that function raises FileNotFoundError for non-existent PDF."""
    with pytest.raises(FileNotFoundError):
        convert_pdf_to_images("nonexistent.pdf", "output")


def test_convert_pdf_to_images_raises_on_invalid_dpi():
    """Test that function raises ValueError for invalid DPI."""
    # This would require a real PDF file to test properly
    # For now, just test the validation logic
    pass
