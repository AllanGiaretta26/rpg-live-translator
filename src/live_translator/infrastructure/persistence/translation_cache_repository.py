from __future__ import annotations

from datetime import datetime, timezone
import unicodedata

from live_translator.domain.interfaces import TranslationCache
from live_translator.domain.models import TranslationResult

from .sqlite_connection import SQLiteConnectionManager


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = " ".join(normalized.split())
    return normalized.casefold()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteTranslationCacheRepository(TranslationCache):
    def __init__(self, database: SQLiteConnectionManager) -> None:
        self._database = database

    def get_by_text(self, source_text: str) -> TranslationResult | None:
        normalized_source_text = _normalize_text(source_text)
        if not normalized_source_text:
            return None

        query = """
        SELECT source_text, translated_text, source_lang, target_lang
        FROM translations
        WHERE normalized_source_text = ?
        """

        with self._database.open() as connection:
            row = connection.execute(query, (normalized_source_text,)).fetchone()

        if row is None:
            return None

        return TranslationResult(
            source_text=row["source_text"],
            translated_text=row["translated_text"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
        )

    def save_translation(self, result: TranslationResult) -> None:
        normalized_source_text = _normalize_text(result.source_text)
        if not normalized_source_text:
            raise ValueError("source_text must not be blank")

        statement = """
        INSERT INTO translations (
            source_text,
            normalized_source_text,
            translated_text,
            source_lang,
            target_lang,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(normalized_source_text) DO UPDATE SET
            source_text = excluded.source_text,
            translated_text = excluded.translated_text,
            source_lang = excluded.source_lang,
            target_lang = excluded.target_lang
        """

        with self._database.open() as connection:
            connection.execute(
                statement,
                (
                    result.source_text,
                    normalized_source_text,
                    result.translated_text,
                    result.source_lang,
                    result.target_lang,
                    _utc_now(),
                ),
            )
