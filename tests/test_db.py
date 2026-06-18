"""Tests for database schema module."""

import pytest
import sqlite3
from pathlib import Path
from src.database.schema import init_db, insert_page, get_pending_pages


def test_init_db_creates_database(tmp_path):
    """Test that init_db creates the database file."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    assert db_path.exists()


def test_insert_page_adds_record(tmp_path):
    """Test that insert_page adds a record to the database."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))

    result = insert_page(str(db_path), "test_page_001", "test.pdf", 1, "test.png")

    assert result is True

    # Verify record exists
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM page_annotations WHERE page_id = ?", ("test_page_001",)
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None


def test_get_pending_pages_returns_pending_only(tmp_path):
    """Test that get_pending_pages returns only pending pages."""
    db_path = tmp_path / "test.db"
    init_db(str(db_path))

    # Insert a pending page
    insert_page(str(db_path), "page_1", "test.pdf", 1, "img1.png")

    pending = get_pending_pages(str(db_path))
    assert len(pending) == 1
    assert pending[0]["page_id"] == "page_1"
