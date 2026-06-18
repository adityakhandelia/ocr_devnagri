"""SQLite database layer for Devanagari OCR annotation platform.

This module provides database initialization and helper functions for managing
page annotations, OCR drafts, ground truth data, and metrics.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from contextlib import contextmanager


# Default database path
DEFAULT_DB_PATH = Path("data/annotations.db")


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize the SQLite database with the required schema.

    Args:
        db_path: Path to the database file. If None, uses default path.
    """
    if db_path is None:
        db_path_obj = DEFAULT_DB_PATH
    else:
        db_path_obj = Path(db_path) if isinstance(db_path, str) else db_path

    # Ensure directory exists
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create the main table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_annotations (
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
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            estimated_cost REAL,
            model_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create API usage tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id TEXT,
            model_name TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            estimated_cost REAL DEFAULT 0.0,
            request_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES page_annotations(page_id)
        )
    """)

    # Create indexes for common queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON page_annotations(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pdf_source ON page_annotations(pdf_source)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_updated_at ON page_annotations(updated_at)
    """)

    conn.commit()
    conn.close()


@contextmanager
def get_db_connection(db_path: Optional[Union[str, Path]] = None):
    """Context manager for database connections.

    Args:
        db_path: Path to the database file. If None, uses default path.

    Yields:
        sqlite3.Connection: Database connection object.
    """
    if db_path is None:
        db_path_obj = DEFAULT_DB_PATH
    else:
        db_path_obj = Path(db_path) if isinstance(db_path, str) else db_path

    conn = sqlite3.connect(str(db_path_obj))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def insert_page(
    db_path: Optional[str],
    page_id: str,
    pdf_source: str,
    page_number: int,
    image_path: str,
) -> bool:
    """Insert a new page record into the database.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.
        pdf_source: Path to the source PDF file.
        page_number: Page number within the PDF.
        image_path: Path to the high-resolution PNG image.

    Returns:
        True if insertion was successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO page_annotations 
                (page_id, pdf_source, page_number, image_path, status)
                VALUES (?, ?, ?, ?, 'pending')
            """,
                (page_id, pdf_source, page_number, image_path),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # Page already exists
        return False
    except Exception as e:
        print(f"Error inserting page: {e}")
        return False


def save_ocr_draft(db_path: Optional[str], page_id: str, ocr_draft: str) -> bool:
    """Save the OCR draft text for a page.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.
        ocr_draft: The OCR draft text.

    Returns:
        True if update was successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE page_annotations 
                SET ocr_draft = ?, updated_at = CURRENT_TIMESTAMP
                WHERE page_id = ?
            """,
                (ocr_draft, page_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving OCR draft: {e}")
        return False


def save_ground_truth(
    db_path: Optional[str],
    page_id: str,
    ground_truth: str,
    status: str = "completed",
    wer: Optional[float] = None,
    cer: Optional[float] = None,
    annotation_time_sec: Optional[float] = None,
) -> bool:
    """Save the corrected ground truth text and metrics for a page.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.
        ground_truth: The corrected ground truth text.
        status: New status ('completed' or 'flagged').
        wer: Word Error Rate (optional).
        cer: Character Error Rate (optional).
        annotation_time_sec: Time spent annotating in seconds (optional).

    Returns:
        True if update was successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE page_annotations 
                SET ground_truth = ?, 
                    status = ?, 
                    wer = ?, 
                    cer = ?, 
                    annotation_time_sec = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE page_id = ?
            """,
                (ground_truth, status, wer, cer, annotation_time_sec, page_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error saving ground truth: {e}")
        return False


def save_token_usage(
    db_path: Optional[str],
    page_id: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    request_type: str = "ocr",
) -> bool:
    """Save API token usage for a page.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.
        model_name: Name of the model used.
        prompt_tokens: Number of prompt tokens used.
        completion_tokens: Number of completion tokens used.
        total_tokens: Total tokens used.
        estimated_cost: Estimated cost in USD.
        request_type: Type of request (e.g., 'ocr', 'transliteration').

    Returns:
        True if save was successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Update page_annotations with token usage
            cursor.execute(
                """
                UPDATE page_annotations 
                SET prompt_tokens = ?,
                    completion_tokens = ?,
                    total_tokens = ?,
                    estimated_cost = ?,
                    model_name = ?
                WHERE page_id = ?
            """,
                (prompt_tokens, completion_tokens, total_tokens, estimated_cost, model_name, page_id),
            )
            
            # Insert into api_usage tracking table
            cursor.execute(
                """
                INSERT INTO api_usage 
                (page_id, model_name, prompt_tokens, completion_tokens, total_tokens, estimated_cost, request_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (page_id, model_name, prompt_tokens, completion_tokens, total_tokens, estimated_cost, request_type),
            )
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving token usage: {e}")
        return False


def get_token_usage_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Get total token usage statistics.

    Args:
        db_path: Path to the database file.

    Returns:
        Dictionary containing:
        - total_prompt_tokens
        - total_completion_tokens
        - total_tokens
        - total_cost
        - total_requests
        - avg_tokens_per_request
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(prompt_tokens), 0) as total_prompt,
                    COALESCE(SUM(completion_tokens), 0) as total_completion,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(estimated_cost), 0.0) as total_cost,
                    COUNT(*) as total_requests,
                    COALESCE(AVG(total_tokens), 0) as avg_tokens
                FROM api_usage
            """)
            
            row = cursor.fetchone()
            
            return {
                "total_prompt_tokens": int(row["total_prompt"]),
                "total_completion_tokens": int(row["total_completion"]),
                "total_tokens": int(row["total_tokens"]),
                "total_cost": round(float(row["total_cost"]), 6),
                "total_requests": int(row["total_requests"]),
                "avg_tokens_per_request": round(float(row["avg_tokens"]), 2),
            }
    except Exception as e:
        print(f"Error fetching token stats: {e}")
        return {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_requests": 0,
            "avg_tokens_per_request": 0.0,
        }


def get_pending_pages(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all pages with 'pending' status.

    Args:
        db_path: Path to the database file.

    Returns:
        List of dictionaries containing page information.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT page_id, pdf_source, page_number, image_path, ocr_draft, status
                FROM page_annotations 
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching pending pages: {e}")
        return []


def get_page_data(db_path: Optional[str], page_id: str) -> Optional[Dict[str, Any]]:
    """Get all data for a specific page.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.

    Returns:
        Dictionary containing page data, or None if not found.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM page_annotations 
                WHERE page_id = ?
            """,
                (page_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching page data: {e}")
        return None


def get_analytics_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Get overall analytics statistics.

    Args:
        db_path: Path to the database file.

    Returns:
        Dictionary containing statistics:
        - total_pages: Total number of pages
        - completed_pages: Number of completed pages
        - pending_pages: Number of pending pages
        - flagged_pages: Number of flagged pages
        - avg_wer: Average Word Error Rate
        - avg_cer: Average Character Error Rate
        - completion_rate: Percentage of completed pages
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Get counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM page_annotations 
                GROUP BY status
            """)
            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            total_pages = sum(status_counts.values())
            completed_pages = status_counts.get("completed", 0)
            pending_pages = status_counts.get("pending", 0)
            flagged_pages = status_counts.get("flagged", 0)

            # Get average error rates for completed pages
            cursor.execute("""
                SELECT AVG(wer) as avg_wer, AVG(cer) as avg_cer
                FROM page_annotations 
                WHERE status = 'completed' AND wer IS NOT NULL
            """)
            row = cursor.fetchone()
            avg_wer = row["avg_wer"] if row["avg_wer"] else 0.0
            avg_cer = row["avg_cer"] if row["avg_cer"] else 0.0

            completion_rate = (
                (completed_pages / total_pages * 100) if total_pages > 0 else 0.0
            )

            return {
                "total_pages": total_pages,
                "completed_pages": completed_pages,
                "pending_pages": pending_pages,
                "flagged_pages": flagged_pages,
                "avg_wer": round(avg_wer, 4) if avg_wer else 0.0,
                "avg_cer": round(avg_cer, 4) if avg_cer else 0.0,
                "completion_rate": round(completion_rate, 2),
            }
    except Exception as e:
        print(f"Error fetching analytics: {e}")
        return {
            "total_pages": 0,
            "completed_pages": 0,
            "pending_pages": 0,
            "flagged_pages": 0,
            "avg_wer": 0.0,
            "avg_cer": 0.0,
            "completion_rate": 0.0,
        }


def update_page_status(db_path: Optional[str], page_id: str, status: str) -> bool:
    """Update the status of a page.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.
        status: New status ('pending', 'completed', or 'flagged').

    Returns:
        True if update was successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE page_annotations 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE page_id = ?
            """,
                (status, page_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating page status: {e}")
        return False


def delete_page(db_path: Optional[str], page_id: str) -> bool:
    """Delete a page record from the database.

    Args:
        db_path: Path to the database file.
        page_id: Unique identifier for the page.

    Returns:
        True if deletion was successful, False otherwise.
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM page_annotations 
                WHERE page_id = ?
            """,
                (page_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting page: {e}")
        return False


def export_to_csv(db_path: Optional[str], output_path: str) -> bool:
    """Export all completed annotations to a CSV file.

    Args:
        db_path: Path to the database file.
        output_path: Path to save the CSV file.

    Returns:
        True if export was successful, False otherwise.
    """
    import pandas as pd

    try:
        with get_db_connection(db_path) as conn:
            df = pd.read_sql_query(
                """
                SELECT * FROM page_annotations 
                WHERE status = 'completed'
                ORDER BY created_at ASC
            """,
                conn,
            )

            df.to_csv(output_path, index=False, encoding="utf-8")
            return True
    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return False
