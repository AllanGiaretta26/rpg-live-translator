from __future__ import annotations

import sqlite3

import pytest

from live_translator.domain.models import GameProfile, TextRegion, TranslationResult
from live_translator.infrastructure.persistence.game_profile_repository import (
    ACTIVE_PROFILE_SETTING_KEY,
    SQLiteGameProfileRepository,
)
from live_translator.infrastructure.persistence.image_cache_repository import SQLiteImageCacheRepository
from live_translator.infrastructure.persistence.settings_repository import SQLiteSettingsRepository
from live_translator.infrastructure.persistence.sqlite_connection import SQLiteConnectionManager
from live_translator.infrastructure.persistence.translation_cache_repository import (
    SQLiteTranslationCacheRepository,
)


@pytest.fixture()
def database_path(tmp_path):
    return tmp_path / "persistence.sqlite3"


@pytest.fixture()
def connection_manager(database_path):
    return SQLiteConnectionManager(database_path)


def test_translation_cache_saves_and_loads_by_normalized_text(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)

    repository.save_translation(
        TranslationResult(
            source_text="  Hello   world  ",
            translated_text="Olá mundo",
            source_lang="en",
            target_lang="pt-BR",
        )
    )

    cached = repository.get_by_text("hello world")

    assert cached is not None
    assert cached.source_text == "  Hello   world  "
    assert cached.translated_text == "Olá mundo"
    assert cached.source_lang == "en"
    assert cached.target_lang == "pt-BR"


def test_translation_cache_enforces_unique_normalized_text(
    connection_manager, database_path
):
    repository = SQLiteTranslationCacheRepository(connection_manager)
    repository.save_translation(
        TranslationResult(source_text="Alpha", translated_text="Um")
    )
    repository.save_translation(
        TranslationResult(source_text="  alpha  ", translated_text="Dois")
    )

    with connection_manager.open() as connection:
        row_count = connection.execute(
            "SELECT COUNT(*) AS count FROM translations"
        ).fetchone()["count"]

    assert row_count == 1
    assert repository.get_by_text("ALPHA").translated_text == "Dois"

    raw_connection = sqlite3.connect(str(database_path))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            raw_connection.execute(
                """
                INSERT INTO translations (
                    source_text,
                    normalized_source_text,
                    translated_text,
                    source_lang,
                    target_lang,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("dup", "alpha", "x", "en", "pt-BR", "2026-01-01T00:00:00Z"),
            )
    finally:
        raw_connection.close()


def test_image_cache_saves_and_loads_by_hash(connection_manager):
    repository = SQLiteImageCacheRepository(connection_manager)

    repository.save_image_result(
        "  ABCDEF1234  ",
        TranslationResult(source_text="Hello", translated_text="Olá"),
    )

    cached = repository.get_by_hash("abcdef1234")

    assert cached is not None
    assert cached.source_text == "Hello"
    assert cached.translated_text == "Olá"


def test_image_cache_enforces_unique_hash(connection_manager, database_path):
    repository = SQLiteImageCacheRepository(connection_manager)

    repository.save_image_result(
        "hash-1", TranslationResult(source_text="A", translated_text="B")
    )
    repository.save_image_result(
        "HASH-1", TranslationResult(source_text="C", translated_text="D")
    )

    with connection_manager.open() as connection:
        row_count = connection.execute(
            "SELECT COUNT(*) AS count FROM image_cache"
        ).fetchone()["count"]

    assert row_count == 1
    assert repository.get_by_hash("hash-1").translated_text == "D"

    raw_connection = sqlite3.connect(str(database_path))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            raw_connection.execute(
                """
                INSERT INTO image_cache (
                    image_hash,
                    source_text,
                    translated_text,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                ("hash-1", "x", "y", "2026-01-01T00:00:00Z"),
            )
    finally:
        raw_connection.close()


def test_settings_repository_stores_updates_and_deletes(connection_manager):
    repository = SQLiteSettingsRepository(connection_manager)

    assert repository.get("missing") is None

    repository.set("language", "pt-BR")
    assert repository.get("language") == "pt-BR"

    repository.set("language", "en")
    assert repository.get("language") == "en"

    repository.delete("language")
    assert repository.get("language") is None


def test_game_profile_repository_saves_and_loads_active_profile(connection_manager):
    settings_repository = SQLiteSettingsRepository(connection_manager)
    repository = SQLiteGameProfileRepository(connection_manager, settings_repository)

    profile = GameProfile(
        name="Main Game",
        window_title="RPG Maker",
        text_region=TextRegion(x=10, y=20, width=300, height=120),
    )
    repository.save(profile)

    loaded = repository.get_active_profile()

    assert loaded == profile
    assert settings_repository.get(ACTIVE_PROFILE_SETTING_KEY) == "Main Game"


def test_game_profile_repository_updates_existing_profile(connection_manager):
    repository = SQLiteGameProfileRepository(connection_manager)

    repository.save(
        GameProfile(
            name="Game A",
            window_title="Window One",
            text_region=TextRegion(x=1, y=2, width=3, height=4),
        )
    )
    repository.save(
        GameProfile(
            name="Game A",
            window_title="Window Two",
            text_region=TextRegion(x=5, y=6, width=7, height=8),
        )
    )

    loaded = repository.get_active_profile()

    assert loaded == GameProfile(
        name="Game A",
        window_title="Window Two",
        text_region=TextRegion(x=5, y=6, width=7, height=8),
    )
