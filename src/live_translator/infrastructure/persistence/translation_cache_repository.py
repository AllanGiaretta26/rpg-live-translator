from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
import unicodedata

from live_translator.domain.interfaces import TranslationCache
from live_translator.domain.models import TranslationResult

from .sqlite_connection import SQLiteConnectionManager


# Mantém folga abaixo do limite de parâmetros do SQLite (o escopo ocupa um slot).
_QUERY_CHUNK_SIZE = 500


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = " ".join(normalized.split())
    return normalized.casefold()


def _normalize_scope(scope: str | None) -> str:
    if scope is None:
        return ""
    return unicodedata.normalize("NFKC", scope).strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteTranslationCacheRepository(TranslationCache):
    def __init__(self, database: SQLiteConnectionManager) -> None:
        self._database = database

    def get_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> TranslationResult | None:
        normalized_source_text = _normalize_text(source_text)
        if not normalized_source_text:
            return None
        normalized_scope = _normalize_scope(scope)

        query = """
        SELECT source_text, translated_text, source_lang, target_lang
        FROM translations
        WHERE scope = ? AND normalized_source_text = ?
        """

        with self._database.open() as connection:
            row = connection.execute(
                query,
                (normalized_scope, normalized_source_text),
            ).fetchone()

        if row is None:
            return None

        return TranslationResult(
            source_text=row["source_text"],
            translated_text=row["translated_text"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
        )

    def get_many_by_text(
        self,
        texts: Sequence[str],
        *,
        scope: str | None = None,
    ) -> dict[str, TranslationResult]:
        # Mapeia cada texto solicitado (original) para sua chave normalizada de
        # cache, mantendo apenas os que normalizam para algo não vazio.
        normalized_by_text: dict[str, str] = {}
        for text in texts:
            key = _normalize_text(text)
            if key:
                normalized_by_text[text] = key
        if not normalized_by_text:
            return {}
        normalized_scope = _normalize_scope(scope)

        unique_keys = list(dict.fromkeys(normalized_by_text.values()))
        rows_by_key: dict[str, TranslationResult] = {}
        with self._database.open() as connection:
            for start in range(0, len(unique_keys), _QUERY_CHUNK_SIZE):
                chunk = unique_keys[start : start + _QUERY_CHUNK_SIZE]
                placeholders = ",".join("?" for _ in chunk)
                rows = connection.execute(
                    f"""
                    SELECT
                        normalized_source_text,
                        source_text,
                        translated_text,
                        source_lang,
                        target_lang
                    FROM translations
                    WHERE scope = ? AND normalized_source_text IN ({placeholders})
                    """,
                    (normalized_scope, *chunk),
                ).fetchall()
                for row in rows:
                    rows_by_key[row["normalized_source_text"]] = TranslationResult(
                        source_text=row["source_text"],
                        translated_text=row["translated_text"],
                        source_lang=row["source_lang"],
                        target_lang=row["target_lang"],
                    )

        return {
            text: rows_by_key[key]
            for text, key in normalized_by_text.items()
            if key in rows_by_key
        }

    def save_translation(
        self,
        result: TranslationResult,
        *,
        scope: str | None = None,
    ) -> None:
        normalized_source_text = _normalize_text(result.source_text)
        if not normalized_source_text:
            raise ValueError("source_text must not be blank")
        normalized_scope = _normalize_scope(scope)

        statement = """
        INSERT INTO translations (
            scope,
            source_text,
            normalized_source_text,
            translated_text,
            source_lang,
            target_lang,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scope, normalized_source_text) DO UPDATE SET
            source_text = excluded.source_text,
            translated_text = excluded.translated_text,
            source_lang = excluded.source_lang,
            target_lang = excluded.target_lang
        """

        with self._database.open() as connection:
            connection.execute(
                statement,
                (
                    normalized_scope,
                    result.source_text,
                    normalized_source_text,
                    result.translated_text,
                    result.source_lang,
                    result.target_lang,
                    _utc_now(),
                ),
            )

    def delete_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> bool:
        normalized_source_text = _normalize_text(source_text)
        if not normalized_source_text:
            return False
        normalized_scope = _normalize_scope(scope)

        with self._database.open() as connection:
            cursor = connection.execute(
                """
                DELETE FROM translations
                WHERE scope = ? AND normalized_source_text = ?
                """,
                (normalized_scope, normalized_source_text),
            )
        return cursor.rowcount > 0
