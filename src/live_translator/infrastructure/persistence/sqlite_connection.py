from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator
import sqlite3


DEFAULT_CONNECTION_TIMEOUT_SECONDS = 5.0


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL DEFAULT '',
    source_text TEXT NOT NULL,
    normalized_source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    source_lang TEXT NOT NULL DEFAULT 'auto',
    target_lang TEXT NOT NULL DEFAULT 'pt-BR',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_hash TEXT NOT NULL UNIQUE,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_term TEXT NOT NULL,
    target_term TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS game_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    window_title TEXT NOT NULL,
    region_x INTEGER NOT NULL,
    region_y INTEGER NOT NULL,
    region_width INTEGER NOT NULL,
    region_height INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rpg_maker_text_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root TEXT NOT NULL,
    data_path TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    source_text TEXT NOT NULL,
    normalized_source_text TEXT NOT NULL,
    text_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    origin_key TEXT NOT NULL,
    map_id INTEGER,
    event_id INTEGER,
    page_index INTEGER,
    command_index INTEGER,
    parameter_index INTEGER,
    database_id INTEGER,
    field_name TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(project_root, origin_key, normalized_source_text)
);

CREATE TABLE IF NOT EXISTS rpg_maker_batch_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER,
    origin TEXT NOT NULL,
    source_text TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

REQUIRED_RPG_MAKER_CATALOG_COLUMNS = {
    "database_id": "INTEGER",
    "field_name": "TEXT",
}


class SQLiteConnectionManager:
    def __init__(
        self,
        database_path: str | Path,
        *,
        timeout_seconds: float = DEFAULT_CONNECTION_TIMEOUT_SECONDS,
    ) -> None:
        self._database_path = Path(database_path)
        self._timeout_seconds = timeout_seconds
        self._init_lock = Lock()
        self._initialized = False

    @property
    def database_path(self) -> Path:
        return self._database_path

    @contextmanager
    def open(self) -> Iterator[sqlite3.Connection]:
        self._ensure_initialized()
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._timeout_seconds,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = self._connect()
            try:
                connection.executescript(SCHEMA_SQL)
                self._migrate(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            self._initialized = True

    def _migrate(self, connection: sqlite3.Connection) -> None:
        self._migrate_translations(connection)
        self._migrate_rpg_maker_catalog(connection)

    def _migrate_rpg_maker_catalog(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            "PRAGMA table_info(rpg_maker_text_catalog)"
        ).fetchall()
        existing_columns = {str(row["name"]) for row in rows}
        for column_name, column_type in REQUIRED_RPG_MAKER_CATALOG_COLUMNS.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE rpg_maker_text_catalog ADD COLUMN {column_name} {column_type}"
                )

    def _migrate_translations(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute("PRAGMA table_info(translations)").fetchall()
        existing_columns = {str(row["name"]) for row in rows}
        if not existing_columns:
            return

        if "scope" not in existing_columns or _has_legacy_translation_unique_index(
            connection
        ):
            _rebuild_translations_table(
                connection, has_scope="scope" in existing_columns
            )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_translations_scope_normalized_source_text
            ON translations(scope, normalized_source_text)
            """
        )


def _has_legacy_translation_unique_index(connection: sqlite3.Connection) -> bool:
    indexes = connection.execute("PRAGMA index_list(translations)").fetchall()
    for index in indexes:
        if not int(index["unique"]):
            continue
        index_name = str(index["name"])
        columns = [
            str(row["name"])
            for row in connection.execute(f"PRAGMA index_info({index_name})").fetchall()
        ]
        if columns == ["normalized_source_text"]:
            return True
    return False


def _rebuild_translations_table(
    connection: sqlite3.Connection,
    *,
    has_scope: bool,
) -> None:
    connection.execute("ALTER TABLE translations RENAME TO translations_legacy")
    connection.execute(
        """
        CREATE TABLE translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL DEFAULT '',
            source_text TEXT NOT NULL,
            normalized_source_text TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            source_lang TEXT NOT NULL DEFAULT 'auto',
            target_lang TEXT NOT NULL DEFAULT 'pt-BR',
            created_at TEXT NOT NULL
        )
        """
    )
    scope_expression = "COALESCE(scope, '')" if has_scope else "''"
    connection.execute(
        f"""
        INSERT INTO translations (
            scope,
            source_text,
            normalized_source_text,
            translated_text,
            source_lang,
            target_lang,
            created_at
        )
        SELECT
            {scope_expression},
            source_text,
            normalized_source_text,
            translated_text,
            source_lang,
            target_lang,
            created_at
        FROM translations_legacy
        GROUP BY {scope_expression}, normalized_source_text
        """
    )
    connection.execute("DROP TABLE translations_legacy")
