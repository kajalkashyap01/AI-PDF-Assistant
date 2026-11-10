
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "documind_history.db"


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =========================================================
# DATABASE INITIALIZATION AND MIGRATION
# =========================================================

def initialize_database() -> None:
    """Create tables and safely migrate existing chat history."""

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
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'New chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE
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

        # Add conversation_id to an existing messages table.
        message_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(messages)"
            ).fetchall()
        }

        if "conversation_id" not in message_columns:
            connection.execute(
                """
                ALTER TABLE messages
                ADD COLUMN conversation_id INTEGER
                REFERENCES conversations(id)
                ON DELETE CASCADE
                """
            )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_document_id
            ON messages(document_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_document_id
            ON conversations(document_id)
            """
        )

        # Put each document's existing messages into one
        # initial conversation. This migration runs only
        # for messages that do not already have a conversation.
        documents_with_old_messages = connection.execute(
            """
            SELECT
                document_id,
                MIN(created_at) AS first_message,
                MAX(created_at) AS last_message
            FROM messages
            WHERE conversation_id IS NULL
            GROUP BY document_id
            """
        ).fetchall()

        for item in documents_with_old_messages:

            document_id = int(item["document_id"])
            first_message = item["first_message"] or current_timestamp()
            last_message = item["last_message"] or first_message

            cursor = connection.execute(
                """
                INSERT INTO conversations (
                    document_id,
                    title,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    document_id,
                    "Previous conversation",
                    first_message,
                    last_message,
                ),
            )

            conversation_id = int(cursor.lastrowid)

            connection.execute(
                """
                UPDATE messages
                SET conversation_id = ?
                WHERE document_id = ?
                  AND conversation_id IS NULL
                """,
                (conversation_id, document_id),
            )


# =========================================================
# DOCUMENT FUNCTIONS
# =========================================================

def save_document(
    name: str,
    fingerprint: str,
    pdf_data: bytes,
    namespace: str,
    page_count: int,
) -> tuple[int, bool]:
    """Save a new PDF or return its existing document ID."""

    now = current_timestamp()

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

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()

    return dict(row) if row else None


def get_document_by_fingerprint(
    fingerprint: str,
) -> dict[str, Any] | None:

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM documents
            WHERE fingerprint = ?
            """,
            (fingerprint,),
        ).fetchone()

    return dict(row) if row else None


def list_documents() -> list[dict[str, Any]]:

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
                COUNT(DISTINCT m.id) AS message_count,
                COUNT(DISTINCT c.id) AS conversation_count
            FROM documents AS d
            LEFT JOIN conversations AS c
                ON c.document_id = d.id
            LEFT JOIN messages AS m
                ON m.conversation_id = c.id
            GROUP BY d.id
            ORDER BY d.updated_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def delete_document(document_id: int) -> None:
    """Delete a saved PDF and its conversations permanently."""

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,),
        )


# =========================================================
# CONVERSATION FUNCTIONS
# =========================================================

def create_conversation(
    document_id: int,
    title: str = "New chat",
) -> int:
    """Create a fresh conversation for an existing PDF."""

    now = current_timestamp()

    with get_connection() as connection:

        document = connection.execute(
            "SELECT id FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()

        if document is None:
            raise ValueError("The requested document does not exist.")

        cursor = connection.execute(
            """
            INSERT INTO conversations (
                document_id,
                title,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (document_id, title, now, now),
        )

        connection.execute(
            """
            UPDATE documents
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, document_id),
        )

        return int(cursor.lastrowid)


def get_conversation(
    conversation_id: int,
) -> dict[str, Any] | None:

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

    return dict(row) if row else None


def list_conversations(
    document_id: int,
) -> list[dict[str, Any]]:
    """Return the saved chats for one PDF, newest first."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.document_id,
                c.title,
                c.created_at,
                c.updated_at,
                COUNT(m.id) AS message_count
            FROM conversations AS c
            LEFT JOIN messages AS m
                ON m.conversation_id = c.id
            WHERE c.document_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.id DESC
            """,
            (document_id,),
        ).fetchall()

    return [dict(row) for row in rows]


# =========================================================
# MESSAGE FUNCTIONS
# =========================================================

def save_message(
    document_id: int,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    conversation_id: int | None = None,
) -> None:
    """Save a message inside a particular conversation."""

    if role not in ("user", "assistant"):
        raise ValueError("Message role must be user or assistant.")

    now = current_timestamp()

    sources_json = json.dumps(
        sources or [],
        ensure_ascii=False,
    )

    with get_connection() as connection:

        if conversation_id is None:
            # Backward-compatible behaviour for old callers.
            latest = connection.execute(
                """
                SELECT id
                FROM conversations
                WHERE document_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (document_id,),
            ).fetchone()

            if latest:
                conversation_id = int(latest["id"])
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO conversations (
                        document_id,
                        title,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (document_id, "New chat", now, now),
                )
                conversation_id = int(cursor.lastrowid)

        conversation = connection.execute(
            """
            SELECT document_id
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

        if conversation is None:
            raise ValueError("The conversation does not exist.")

        if int(conversation["document_id"]) != document_id:
            raise ValueError(
                "The conversation does not belong to this document."
            )

        connection.execute(
            """
            INSERT INTO messages (
                document_id,
                conversation_id,
                role,
                content,
                sources,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                conversation_id,
                role,
                content,
                sources_json,
                now,
            ),
        )

        # Use the first user question as the conversation title.
        if role == "user":
            title_row = connection.execute(
                """
                SELECT title
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()

            if title_row and title_row["title"] == "New chat":
                title = content.strip().replace("\n", " ")
                if len(title) > 55:
                    title = title[:52] + "..."

                connection.execute(
                    """
                    UPDATE conversations
                    SET title = ?
                    WHERE id = ?
                    """,
                    (title or "New chat", conversation_id),
                )

        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, conversation_id),
        )

        connection.execute(
            """
            UPDATE documents
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, document_id),
        )


def get_messages(
    conversation_id: int,
) -> list[dict[str, Any]]:
    """Load messages from one conversation only."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content, sources, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
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


def delete_conversation(conversation_id: int) -> None:
    """Delete one conversation without deleting its PDF."""

    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        )
