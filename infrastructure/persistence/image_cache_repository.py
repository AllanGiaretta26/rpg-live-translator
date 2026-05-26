from __future__ import annotations

from datetime import datetime, timezone

from domain.interfaces import ImageCache
from domain.models import TranslationResult

from .sqlite_connection import SQLiteConnectionManager


def _normalize_hash(image_hash: str) -> str:
    return image_hash.strip().casefold()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteImageCacheRepository(ImageCache):
    def __init__(self, database: SQLiteConnectionManager) -> None:
        self._database = database

    def get_by_hash(self, image_hash: str) -> TranslationResult | None:
        normalized_image_hash = _normalize_hash(image_hash)
        if not normalized_image_hash:
            return None

        query = """
        SELECT source_text, translated_text
        FROM image_cache
        WHERE image_hash = ?
        """

        with self._database.open() as connection:
            row = connection.execute(query, (normalized_image_hash,)).fetchone()

        if row is None:
            return None

        return TranslationResult(
            source_text=row["source_text"],
            translated_text=row["translated_text"],
        )

    def save_image_result(self, image_hash: str, result: TranslationResult) -> None:
        normalized_image_hash = _normalize_hash(image_hash)
        if not normalized_image_hash:
            raise ValueError("image_hash must not be blank")

        statement = """
        INSERT INTO image_cache (
            image_hash,
            source_text,
            translated_text,
            created_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(image_hash) DO UPDATE SET
            source_text = excluded.source_text,
            translated_text = excluded.translated_text
        """

        with self._database.open() as connection:
            connection.execute(
                statement,
                (
                    normalized_image_hash,
                    result.source_text,
                    result.translated_text,
                    _utc_now(),
                ),
            )
