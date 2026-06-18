"""SQLite persistence layer for the PDF OCR pipeline.

Tracks the relationship between PDFs, their page images, and OCR text files,
plus processing status and token/cost metrics.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_DB_PATH = Path("data/pipeline.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pdf_name TEXT NOT NULL,
    pdf_path TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    ocr_text_path TEXT,
    ocr_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (ocr_status IN ('pending', 'processing', 'done', 'failed')),
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost REAL DEFAULT 0.0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (pdf_name, page_number)
);

CREATE INDEX IF NOT EXISTS idx_pdf_name ON pipeline_pages(pdf_name);
CREATE INDEX IF NOT EXISTS idx_status ON pipeline_pages(ocr_status);
"""


def get_db_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Return a connection to the pipeline database."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_pipeline_db(db_path: Optional[Path] = None) -> None:
    """Create the pipeline tracking tables if they don't exist."""
    conn = get_db_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def upsert_page(
    pdf_name: str,
    pdf_path: str,
    page_number: int,
    image_path: str,
    ocr_text_path: Optional[str] = None,
    ocr_status: str = "pending",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost: float = 0.0,
    error_message: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Insert or update a pipeline page record."""
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO pipeline_pages (
                pdf_name, pdf_path, page_number, image_path, ocr_text_path,
                ocr_status, prompt_tokens, completion_tokens, total_tokens,
                estimated_cost, error_message, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pdf_name, page_number) DO UPDATE SET
                pdf_path = excluded.pdf_path,
                image_path = excluded.image_path,
                ocr_text_path = excluded.ocr_text_path,
                ocr_status = excluded.ocr_status,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                total_tokens = excluded.total_tokens,
                estimated_cost = excluded.estimated_cost,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
            """,
            (
                pdf_name,
                str(pdf_path),
                page_number,
                str(image_path),
                str(ocr_text_path) if ocr_text_path else None,
                ocr_status,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                estimated_cost,
                error_message,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def mark_page_done(
    pdf_name: str,
    page_number: int,
    ocr_text_path: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    db_path: Optional[Path] = None,
) -> None:
    """Mark a page as successfully OCR'd."""
    upsert_page(
        pdf_name=pdf_name,
        pdf_path="",
        page_number=page_number,
        image_path="",
        ocr_text_path=ocr_text_path,
        ocr_status="done",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        db_path=db_path,
    )


def mark_page_failed(
    pdf_name: str,
    page_number: int,
    error_message: str,
    db_path: Optional[Path] = None,
) -> None:
    """Mark a page as failed."""
    upsert_page(
        pdf_name=pdf_name,
        pdf_path="",
        page_number=page_number,
        image_path="",
        ocr_text_path=None,
        ocr_status="failed",
        error_message=error_message,
        db_path=db_path,
    )


def get_pdf_progress(pdf_name: str, db_path: Optional[Path] = None) -> Dict[str, any]:
    """Return processing progress for a given PDF."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT ocr_status, COUNT(*) as count,
                   SUM(prompt_tokens) as prompt_tokens,
                   SUM(completion_tokens) as completion_tokens,
                   SUM(total_tokens) as total_tokens,
                   SUM(estimated_cost) as estimated_cost
            FROM pipeline_pages
            WHERE pdf_name = ?
            GROUP BY ocr_status
            """,
            (pdf_name,),
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM pipeline_pages WHERE pdf_name = ?",
            (pdf_name,),
        ).fetchone()[0]

        status_counts = {row["ocr_status"]: row["count"] for row in rows}
        done = status_counts.get("done", 0)
        failed = status_counts.get("failed", 0)
        pending = status_counts.get("pending", 0)
        processing = status_counts.get("processing", 0)

        prompt_tokens = sum(row["prompt_tokens"] or 0 for row in rows)
        completion_tokens = sum(row["completion_tokens"] or 0 for row in rows)
        total_tokens = sum(row["total_tokens"] or 0 for row in rows)
        estimated_cost = sum(row["estimated_cost"] or 0 for row in rows)

        return {
            "pdf_name": pdf_name,
            "total_pages": total,
            "done": done,
            "failed": failed,
            "pending": pending,
            "processing": processing,
            "percent_complete": round((done / total) * 100, 2) if total else 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": round(estimated_cost, 4),
        }
    finally:
        conn.close()


def get_page_records(
    pdf_name: str, db_path: Optional[Path] = None
) -> List[Dict[str, any]]:
    """Return all page records for a PDF."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT * FROM pipeline_pages
            WHERE pdf_name = ?
            ORDER BY page_number
            """,
            (pdf_name,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_pdfs_progress(db_path: Optional[Path] = None) -> List[Dict[str, any]]:
    """Return progress summary for all PDFs."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT pdf_name FROM pipeline_pages ORDER BY pdf_name"
        ).fetchall()
        return [get_pdf_progress(row["pdf_name"], db_path) for row in rows]
    finally:
        conn.close()


def record_exists(
    pdf_name: str, page_number: int, db_path: Optional[Path] = None
) -> bool:
    """Check whether a page record already exists."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM pipeline_pages WHERE pdf_name = ? AND page_number = ?",
            (pdf_name, page_number),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
