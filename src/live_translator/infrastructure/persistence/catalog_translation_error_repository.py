from __future__ import annotations

from datetime import datetime, timezone

from live_translator.domain.interfaces import CatalogTranslationErrorRepository
from live_translator.domain.models import CatalogTranslationError

from .sqlite_connection import SQLiteConnectionManager


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteCatalogTranslationErrorRepository(CatalogTranslationErrorRepository):
    def __init__(self, database: SQLiteConnectionManager) -> None:
        self._database = database

    def clear_last_batch_errors(self) -> None:
        with self._database.open() as connection:
            connection.execute("DELETE FROM rpg_maker_batch_errors")

    def save_error(self, error: CatalogTranslationError) -> None:
        with self._database.open() as connection:
            connection.execute(
                """
                INSERT INTO rpg_maker_batch_errors (
                    entry_id,
                    origin,
                    source_text,
                    error_message,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    error.entry_id,
                    error.origin,
                    error.source_text,
                    error.error_message,
                    _utc_now(),
                ),
            )

    def list_last_batch_errors(self) -> list[CatalogTranslationError]:
        with self._database.open() as connection:
            rows = connection.execute(
                """
                SELECT entry_id, origin, source_text, error_message, created_at
                FROM rpg_maker_batch_errors
                ORDER BY id
                """
            ).fetchall()

        return [
            CatalogTranslationError(
                entry_id=row["entry_id"],
                origin=row["origin"],
                source_text=row["source_text"],
                error_message=row["error_message"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
