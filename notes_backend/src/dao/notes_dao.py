"""
SQLite Data Access Object (DAO) for Notes.

Key requirement: the SQLite database absolute path MUST be read at runtime from:
simple-notes-app-307703-307713/database/db_connection.txt

This module uses sqlite3 with row_factory=sqlite3.Row and stores timestamps in UTC.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass(frozen=True)
class _DBConfig:
    """Internal container for database config."""

    db_path: str


def _utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp string (timezone-aware)."""
    return datetime.now(timezone.utc).isoformat()


def _parse_db_path_from_db_connection_txt(contents: str) -> str:
    """
    Parse the absolute sqlite file path from db_connection.txt contents.

    The file typically contains a line like:
    # File path: /abs/path/to/myapp.db
    """
    match = re.search(r"^\s*#\s*File path:\s*(.+?)\s*$", contents, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(
            "Could not find '# File path: ...' line in database/db_connection.txt."
        )
    db_path = match.group(1).strip()
    if not db_path.startswith("/"):
        raise RuntimeError(
            "Parsed SQLite DB path is not absolute. Refusing to proceed."
        )
    return db_path


def _load_db_config() -> _DBConfig:
    """
    Load DB config by reading the absolute SQLite path from the shared database container file.

    NOTE: Do not hardcode DB paths. This reads at runtime to keep the module portable across environments.
    """
    # This backend container lives at: simple-notes-app-307703-307714/notes_backend/src/dao/notes_dao.py
    # We need to reach:            ../.. (notes_backend) -> .. (workspace) -> ../simple-notes-app-307703-307713/database/db_connection.txt
    base_dir = os.path.dirname(os.path.abspath(__file__))

    db_connection_txt = os.path.abspath(
        os.path.join(
            base_dir,
            "..",  # src
            "..",  # notes_backend
            "..",  # simple-notes-app-307703-307714 (workspace)
            "..",  # code-generation (base folder)
            "simple-notes-app-307703-307713",
            "database",
            "db_connection.txt",
        )
    )

    try:
        with open(db_connection_txt, "r", encoding="utf-8") as f:
            contents = f.read()
    except FileNotFoundError as e:
        raise RuntimeError(
            f"db_connection.txt not found at expected path: {db_connection_txt}. "
            "Ensure the database container has created this file."
        ) from e

    db_path = _parse_db_path_from_db_connection_txt(contents)

    # Basic sanity check; DB file might be created on first run, so we don't require existence,
    # but we do ensure directory exists.
    parent_dir = os.path.dirname(db_path)
    if not os.path.isdir(parent_dir):
        raise RuntimeError(
            f"SQLite DB directory does not exist: {parent_dir}. Parsed from db_connection.txt."
        )

    return _DBConfig(db_path=db_path)


@contextmanager
def _get_conn():
    """Context manager providing a sqlite3 connection with Row factory and FK enabled."""
    cfg = _load_db_config()
    conn = sqlite3.connect(cfg.db_path, check_same_thread=False)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_note_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to a serializable dict (timestamps left as ISO strings)."""
    return {
        "id": int(row["id"]),
        "title": str(row["title"]),
        "content": str(row["content"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


# PUBLIC_INTERFACE
def list_notes() -> List[dict]:
    """List notes ordered by updated_at descending."""
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        return [_row_to_note_dict(r) for r in rows]


# PUBLIC_INTERFACE
def get_note(note_id: int) -> Optional[dict]:
    """Get a single note by ID. Returns None if not found."""
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        ).fetchone()
        return _row_to_note_dict(row) if row else None


# PUBLIC_INTERFACE
def create_note(title: str, content: str) -> dict:
    """Create a note and return the created record."""
    now = _utc_now_iso()
    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO notes (title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (title, content, now, now),
        )
        note_id = int(cur.lastrowid)
    # Re-fetch to ensure we return exactly what's stored
    created = get_note(note_id)
    if created is None:
        raise RuntimeError("Failed to fetch note after creation.")
    return created


# PUBLIC_INTERFACE
def update_note(note_id: int, title: Optional[str], content: Optional[str]) -> Optional[dict]:
    """
    Update a note (partial update allowed). Returns updated note dict, or None if not found.

    If both title and content are None, this function only refreshes updated_at.
    """
    now = _utc_now_iso()
    with _get_conn() as conn:
        existing = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not existing:
            return None

        if title is not None and content is not None:
            conn.execute(
                """
                UPDATE notes
                SET title = ?, content = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, content, now, note_id),
            )
        elif title is not None:
            conn.execute(
                """
                UPDATE notes
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, note_id),
            )
        elif content is not None:
            conn.execute(
                """
                UPDATE notes
                SET content = ?, updated_at = ?
                WHERE id = ?
                """,
                (content, now, note_id),
            )
        else:
            conn.execute(
                """
                UPDATE notes
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, note_id),
            )

    updated = get_note(note_id)
    if updated is None:
        # Very unlikely: was deleted after the update transaction committed.
        return None
    return updated


# PUBLIC_INTERFACE
def delete_note(note_id: int) -> bool:
    """Delete a note by ID. Returns True if deleted, False if note did not exist."""
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0
