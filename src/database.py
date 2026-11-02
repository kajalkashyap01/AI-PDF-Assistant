
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Store the database in src/data.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "documind_history.db"


def get_connection() -> sqlite3.Connection:
    """Create a connection to the local SQLite database."""

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database() -> None:
    """Create the document and chat-history tables if needed."""

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                pdf_data BLOB NOT NULL,
                namespace TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_document_id
            ON messages(document_id)
            """
        )


def save_document(
    name: str,
    fingerprint: str,
    pdf_data: bytes,
    namespace: str,
    page_count: int,
) -> tuple[int, bool]:
    """
    Save a new PDF or find an already saved PDF with the same fingerprint.

    Returns:
        (document_id, is_new_document)
    """

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:

        existing = connection.execute(
            """
            SELECT id
            FROM documents
            WHERE fingerprint = ?
            """,
            (fingerprint,),
        ).fetchone()

        if existing:
            document_id = int(existing["id"])

            connection.execute(
                """
                UPDATE documents
                SET name = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, now, document_id),
            )

            return document_id, False

        cursor = connection.execute(
            """
            INSERT INTO documents (
                name,
                fingerprint,
                pdf_data,
                namespace,
                page_count,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                fingerprint,
                sqlite3.Binary(pdf_data),
                namespace,
                page_count,
                now,
                now,
            ),
        )

        return int(cursor.lastrowid), True


def get_document(document_id: int) -> dict[str, Any] | None:
    """Retrieve one saved document, including its PDF bytes."""

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT *
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_document_by_fingerprint(
    fingerprint: str,
) -> dict[str, Any] | None:
    """Find a saved PDF using its content fingerprint."""

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT *
            FROM documents
            WHERE fingerprint = ?
            """,
            (fingerprint,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def list_documents() -> list[dict[str, Any]]:
    """Return saved document details, newest first."""

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                d.id,
                d.name,
                d.fingerprint,
                d.namespace,
                d.page_count,
                d.created_at,
                d.updated_at,
                COUNT(m.id) AS message_count
            FROM documents AS d
            LEFT JOIN messages AS m
                ON d.id = m.document_id
            GROUP BY d.id
            ORDER BY d.updated_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def save_message(
    document_id: int,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> None:
    """Save a chat message and its retrieved source context."""

    if role not in ("user", "assistant"):
        raise ValueError("Message role must be user or assistant.")

    now = datetime.now(timezone.utc).isoformat()

    sources_json = json.dumps(
        sources or [],
        ensure_ascii=False,
    )

    with get_connection() as connection:

        connection.execute(
            """
            INSERT INTO messages (
                document_id,
                role,
                content,
                sources,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                document_id,
                role,
                content,
                sources_json,
                now,
            ),
        )

        connection.execute(
            """
            UPDATE documents
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, document_id),
        )


def get_messages(document_id: int) -> list[dict[str, Any]]:
    """Load all chat messages belonging to a document."""

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT role, content, sources, created_at
            FROM messages
            WHERE document_id = ?
            ORDER BY id ASC
            """,
            (document_id,),
        ).fetchall()

    messages = []

    for row in rows:

        try:
            sources = json.loads(row["sources"] or "[]")
        except (json.JSONDecodeError, TypeError):
            sources = []

        messages.append({
            "role": row["role"],
            "content": row["content"],
            "sources": sources,
            "created_at": row["created_at"],
        })

    return messages


def delete_document(document_id: int) -> None:
    """
    Delete a document and its chat history from SQLite.

    This does not delete vectors from Pinecone.
    """

    with get_connection() as connection:

        connection.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (document_id,),
        )
