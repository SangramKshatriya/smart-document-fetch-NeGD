import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from config import DATA_DIR, DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _ensure_column(connection: sqlite3.Connection, name: str, definition: str) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()
    }
    if name not in columns:
        connection.execute(f"ALTER TABLE documents ADD COLUMN {name} {definition}")


def initialize_database() -> None:
    connection = get_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                extension TEXT,
                size INTEGER DEFAULT 0,
                modified_time REAL DEFAULT 0,
                content TEXT DEFAULT '',
                content_hash TEXT DEFAULT '',
                document_type TEXT DEFAULT '',
                language TEXT DEFAULT '',
                indexed_time REAL DEFAULT 0,
                opened_time REAL DEFAULT 0,
                extraction_status TEXT DEFAULT 'ok',
                extraction_error TEXT DEFAULT ''
            )
            """
        )
        # Migrate the old database schema in-place when possible.
        for column, definition in (
            ("content_hash", "TEXT DEFAULT ''"),
            ("document_type", "TEXT DEFAULT ''"),
            ("language", "TEXT DEFAULT ''"),
            ("indexed_time", "REAL DEFAULT 0"),
            ("opened_time", "REAL DEFAULT 0"),
            ("extraction_status", "TEXT DEFAULT 'ok'"),
            ("extraction_error", "TEXT DEFAULT ''"),
        ):
            _ensure_column(connection, column, definition)

        fts_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents_fts'"
        ).fetchone() is not None
        if fts_exists:
            fts_columns = {row[1] for row in connection.execute("PRAGMA table_info(documents_fts)").fetchall()}
            if not {"name", "content", "path", "document_type"}.issubset(fts_columns):
                connection.execute("DROP TABLE documents_fts")
                fts_exists = False
        if not fts_exists:
            connection.execute(
                """
                CREATE VIRTUAL TABLE documents_fts USING fts5(
                    name, content, path, document_type, tokenize='unicode61'
                )
                """
            )
            connection.commit()
            sync_fts(connection)
        else:
            doc_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            fts_count = connection.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
            if doc_count != fts_count:
                sync_fts(connection)
    finally:
        connection.close()


def sync_fts(connection: Optional[sqlite3.Connection] = None) -> None:
    owns_connection = connection is None
    connection = connection or get_connection()
    try:
        connection.execute("DELETE FROM documents_fts")
        rows = connection.execute(
            "SELECT id, name, content, path, document_type FROM documents"
        ).fetchall()
        connection.executemany(
            """
            INSERT INTO documents_fts(rowid, name, content, path, document_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (row["id"], row["name"], row["content"] or "", row["path"], row["document_type"] or "")
                for row in rows
            ],
        )
        connection.commit()
    finally:
        if owns_connection:
            connection.close()


def get_setting(key: str, default: str = "") -> str:
    initialize_database()
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row and row["value"] is not None else default
    finally:
        connection.close()


def set_setting(key: str, value: str) -> None:
    initialize_database()
    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO app_settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        connection.commit()
    finally:
        connection.close()


def get_document_by_path(file_path: str):
    initialize_database()
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM documents WHERE path = ?", (str(Path(file_path).resolve()),)
        ).fetchone()
    finally:
        connection.close()


def upsert_document(
    *,
    name: str,
    path: str,
    extension: str,
    size: int,
    modified_time: float,
    content: str,
    content_hash: str,
    document_type: str,
    language: str,
    extraction_status: str = "ok",
    extraction_error: str = "",
) -> int:
    initialize_database()
    normalized_path = str(Path(path).resolve())
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO documents (
                name, path, extension, size, modified_time, content,
                content_hash, document_type, language, indexed_time,
                extraction_status, extraction_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'), ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name = excluded.name,
                extension = excluded.extension,
                size = excluded.size,
                modified_time = excluded.modified_time,
                content = excluded.content,
                content_hash = excluded.content_hash,
                document_type = excluded.document_type,
                language = excluded.language,
                indexed_time = excluded.indexed_time,
                extraction_status = excluded.extraction_status,
                extraction_error = excluded.extraction_error
            """,
            (
                name, normalized_path, extension, size, modified_time, content,
                content_hash, document_type, language, extraction_status, extraction_error,
            ),
        )
        row = connection.execute(
            "SELECT id FROM documents WHERE path = ?", (normalized_path,)
        ).fetchone()
        document_id = int(row["id"])
        connection.execute("DELETE FROM documents_fts WHERE rowid = ?", (document_id,))
        connection.execute(
            """
            INSERT INTO documents_fts(rowid, name, content, path, document_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, name, content or "", normalized_path, document_type or ""),
        )
        connection.commit()
        return document_id
    finally:
        connection.close()


def mark_opened(file_path: str) -> None:
    initialize_database()
    normalized_path = str(Path(file_path).resolve())
    connection = get_connection()
    try:
        connection.execute(
            "UPDATE documents SET opened_time = strftime('%s','now') WHERE path = ?",
            (normalized_path,),
        )
        connection.commit()
    finally:
        connection.close()


def delete_document_by_path(file_path: str) -> None:
    initialize_database()
    normalized_path = str(Path(file_path).resolve())
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id FROM documents WHERE path = ?", (normalized_path,)
        ).fetchone()
        if row:
            connection.execute("DELETE FROM documents_fts WHERE rowid = ?", (row["id"],))
        connection.execute("DELETE FROM documents WHERE path = ?", (normalized_path,))
        connection.commit()
    finally:
        connection.close()


def delete_documents_not_in_paths(valid_paths: Iterable[str], root_path: Optional[str] = None) -> int:
    initialize_database()
    normalized_paths = {str(Path(path).resolve()) for path in valid_paths}
    connection = get_connection()
    try:
        rows = connection.execute("SELECT id, path FROM documents").fetchall()
        deleted = 0
        for row in rows:
            candidate = Path(row["path"])
            if root_path:
                try:
                    inside_root = candidate.is_relative_to(Path(root_path).resolve())
                except AttributeError:
                    try:
                        candidate.relative_to(Path(root_path).resolve())
                        inside_root = True
                    except ValueError:
                        inside_root = False
                if not inside_root:
                    continue
            if row["path"] not in normalized_paths:
                connection.execute("DELETE FROM documents_fts WHERE rowid = ?", (row["id"],))
                connection.execute("DELETE FROM documents WHERE id = ?", (row["id"],))
                deleted += 1
        connection.commit()
        return deleted
    finally:
        connection.close()


def get_all_documents():
    initialize_database()
    connection = get_connection()
    try:
        return connection.execute(
            "SELECT * FROM documents ORDER BY name COLLATE NOCASE"
        ).fetchall()
    finally:
        connection.close()


def get_recent_documents(limit: int = 10):
    initialize_database()
    connection = get_connection()
    try:
        return connection.execute(
            """
            SELECT * FROM documents
            WHERE opened_time > 0
            ORDER BY opened_time DESC, name COLLATE NOCASE
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()


def get_document_count() -> int:
    initialize_database()
    connection = get_connection()
    try:
        row = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return int(row["count"])
    finally:
        connection.close()


def clear_database() -> None:
    initialize_database()
    connection = get_connection()
    try:
        connection.execute("DELETE FROM documents_fts")
        connection.execute("DELETE FROM documents")
        connection.commit()
    finally:
        connection.close()
