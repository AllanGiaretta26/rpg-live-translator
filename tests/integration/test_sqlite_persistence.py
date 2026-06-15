from __future__ import annotations

import sqlite3

import pytest

from live_translator.domain.models import (
    CatalogTranslationError,
    GameProfile,
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextOrigin,
    RpgMakerTextType,
    RpgMakerVersion,
    TextRegion,
    TranslationResult,
)
from live_translator.infrastructure.persistence.catalog_translation_error_repository import (
    SQLiteCatalogTranslationErrorRepository,
)
from live_translator.infrastructure.persistence.game_profile_repository import (
    ACTIVE_PROFILE_SETTING_KEY,
    SQLiteGameProfileRepository,
)
from live_translator.infrastructure.persistence.image_cache_repository import (
    SQLiteImageCacheRepository,
)
from live_translator.infrastructure.persistence.rpg_maker_catalog_repository import (
    SQLiteRpgMakerTextCatalogRepository,
)
from live_translator.infrastructure.persistence.settings_repository import (
    SQLiteSettingsRepository,
)
from live_translator.infrastructure.persistence.sqlite_connection import (
    SQLiteConnectionManager,
)
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


def test_translation_cache_is_scoped_by_project_root(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)

    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola A"),
        scope="C:/game-a",
    )
    repository.save_translation(
        TranslationResult(source_text="  hello  ", translated_text="Ola B"),
        scope="C:/game-b",
    )
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola global"),
    )

    assert repository.get_by_text("HELLO", scope="C:/game-a").translated_text == "Ola A"
    assert repository.get_by_text("hello", scope="C:/game-b").translated_text == "Ola B"
    assert repository.get_by_text("hello").translated_text == "Ola global"

    with connection_manager.open() as connection:
        row_count = connection.execute(
            "SELECT COUNT(*) AS count FROM translations"
        ).fetchone()["count"]

    assert row_count == 3


def test_translation_cache_get_many_by_text_returns_only_cached(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola")
    )
    repository.save_translation(
        TranslationResult(source_text="World", translated_text="Mundo")
    )

    found = repository.get_many_by_text(["  hello  ", "WORLD", "missing", "   "])

    assert set(found) == {"  hello  ", "WORLD"}
    assert found["  hello  "].translated_text == "Ola"
    assert found["WORLD"].translated_text == "Mundo"


def test_translation_cache_get_many_by_text_is_scoped(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola A"),
        scope="C:/game-a",
    )
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola global"),
    )

    scoped = repository.get_many_by_text(["Hello"], scope="C:/game-a")
    global_scope = repository.get_many_by_text(["Hello"])

    assert scoped["Hello"].translated_text == "Ola A"
    assert global_scope["Hello"].translated_text == "Ola global"
    assert repository.get_many_by_text(["Hello"], scope="C:/game-b") == {}


def test_translation_cache_get_many_by_text_handles_large_batches(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)
    texts = [f"Line {index}" for index in range(1200)]
    for text in texts:
        repository.save_translation(
            TranslationResult(source_text=text, translated_text=f"pt:{text}")
        )

    found = repository.get_many_by_text(texts)

    assert len(found) == 1200
    assert found["Line 999"].translated_text == "pt:Line 999"


def test_sqlite_connection_initializes_schema_only_once(database_path):
    class CountingConnectionManager(SQLiteConnectionManager):
        schema_runs = 0

        def _ensure_initialized(self) -> None:
            already = self._initialized
            super()._ensure_initialized()
            if not already:
                type(self).schema_runs += 1

    manager = CountingConnectionManager(database_path)
    repository = SQLiteTranslationCacheRepository(manager)

    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola")
    )
    for _ in range(5):
        repository.get_by_text("Hello")

    assert CountingConnectionManager.schema_runs == 1
    assert repository.get_by_text("Hello").translated_text == "Ola"


def test_translation_cache_deletes_by_normalized_text(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)
    repository.save_translation(
        TranslationResult(source_text="  Hello   world  ", translated_text="Olá mundo")
    )

    assert repository.delete_by_text("hello world") is True
    assert repository.get_by_text("Hello world") is None
    assert repository.delete_by_text("Hello world") is False


def test_translation_cache_deletes_only_matching_scope(connection_manager):
    repository = SQLiteTranslationCacheRepository(connection_manager)
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola A"),
        scope="C:/game-a",
    )
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola B"),
        scope="C:/game-b",
    )

    assert repository.delete_by_text("hello", scope="C:/game-a") is True

    assert repository.get_by_text("hello", scope="C:/game-a") is None
    assert repository.get_by_text("hello", scope="C:/game-b").translated_text == "Ola B"


def test_sqlite_connection_migrates_legacy_translation_cache_scope(database_path):
    raw_connection = sqlite3.connect(str(database_path))
    try:
        raw_connection.executescript(
            """
            CREATE TABLE translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                normalized_source_text TEXT NOT NULL UNIQUE,
                translated_text TEXT NOT NULL,
                source_lang TEXT NOT NULL DEFAULT 'auto',
                target_lang TEXT NOT NULL DEFAULT 'pt-BR',
                created_at TEXT NOT NULL
            );
            INSERT INTO translations (
                source_text,
                normalized_source_text,
                translated_text,
                source_lang,
                target_lang,
                created_at
            )
            VALUES (
                'Hello',
                'hello',
                'Ola legado',
                'en',
                'pt-BR',
                '2026-01-01T00:00:00Z'
            );
            """
        )
        raw_connection.commit()
    finally:
        raw_connection.close()

    connection_manager = SQLiteConnectionManager(database_path)
    repository = SQLiteTranslationCacheRepository(connection_manager)

    assert repository.get_by_text("hello").translated_text == "Ola legado"
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola A"),
        scope="C:/game-a",
    )
    repository.save_translation(
        TranslationResult(source_text="Hello", translated_text="Ola B"),
        scope="C:/game-b",
    )

    assert repository.get_by_text("hello", scope="C:/game-a").translated_text == "Ola A"
    assert repository.get_by_text("hello", scope="C:/game-b").translated_text == "Ola B"


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


def test_rpg_maker_catalog_replaces_project_entries(connection_manager, tmp_path):
    repository = SQLiteRpgMakerTextCatalogRepository(connection_manager)
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=tmp_path / "Game" / "www" / "data",
        version=RpgMakerVersion.MZ,
    )
    first_entry = RpgMakerTextEntry(
        source_text="Hello",
        text_type=RpgMakerTextType.MESSAGE,
        origin=RpgMakerTextOrigin(
            file_name="Map001.json",
            origin_key="Map001.json|1|2|0|3|0",
            map_id=1,
            event_id=2,
            page_index=0,
            command_index=3,
            parameter_index=0,
        ),
    )
    second_entry = RpgMakerTextEntry(
        source_text="Goodbye",
        text_type=RpgMakerTextType.MESSAGE,
        origin=RpgMakerTextOrigin(
            file_name="Map001.json",
            origin_key="Map001.json|1|2|0|4|0",
            map_id=1,
            event_id=2,
            page_index=0,
            command_index=4,
            parameter_index=0,
        ),
    )

    assert repository.replace_project_entries(project, [first_entry, second_entry]) == 2
    assert repository.replace_project_entries(project, [second_entry]) == 1

    entries = repository.list_project_entries(project)

    assert entries == [
        RpgMakerTextEntry(
            id=entries[0].id,
            source_text="Goodbye",
            text_type=RpgMakerTextType.MESSAGE,
            origin=second_entry.origin,
        )
    ]
    assert repository.count_project_entries(project) == 1
    assert repository.get_entry(entries[0].id) == entries[0]


def test_rpg_maker_catalog_saves_large_batch(connection_manager, tmp_path):
    repository = SQLiteRpgMakerTextCatalogRepository(connection_manager)
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=tmp_path / "Game" / "www" / "data",
        version=RpgMakerVersion.MZ,
    )
    entries = [
        RpgMakerTextEntry(
            source_text=f"Line {index}",
            text_type=RpgMakerTextType.MESSAGE,
            origin=RpgMakerTextOrigin(
                file_name="Map001.json",
                origin_key=f"Map001.json|1|2|0|{index}|0",
                map_id=1,
                event_id=2,
                page_index=0,
                command_index=index,
                parameter_index=0,
            ),
        )
        for index in range(50)
    ]

    saved = repository.replace_project_entries(project, entries)

    assert saved == 50
    assert repository.count_project_entries(project) == 50
    # Reexecutar com um subconjunto substitui as entradas do projeto
    # (caminho executemany).
    assert repository.replace_project_entries(project, entries[:10]) == 10
    assert repository.count_project_entries(project) == 10


def test_rpg_maker_catalog_preserves_database_origin(connection_manager, tmp_path):
    repository = SQLiteRpgMakerTextCatalogRepository(connection_manager)
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=tmp_path / "Game" / "www" / "data",
        version=RpgMakerVersion.MZ,
    )
    database_entry = RpgMakerTextEntry(
        source_text="Potion",
        text_type=RpgMakerTextType.ITEM_NAME,
        origin=RpgMakerTextOrigin(
            file_name="Items.json",
            origin_key="Items.json|database|1|name",
            database_id=1,
            field_name="name",
        ),
    )

    assert repository.replace_project_entries(project, [database_entry]) == 1

    entries = repository.list_project_entries(project)

    assert entries == [
        RpgMakerTextEntry(
            id=entries[0].id,
            source_text="Potion",
            text_type=RpgMakerTextType.ITEM_NAME,
            origin=database_entry.origin,
        )
    ]
    assert repository.get_entry(entries[0].id) == entries[0]


def test_rpg_maker_catalog_lists_project_entries_with_limit_and_offset(
    connection_manager,
    tmp_path,
):
    repository = SQLiteRpgMakerTextCatalogRepository(connection_manager)
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=tmp_path / "Game" / "www" / "data",
        version=RpgMakerVersion.MZ,
    )
    entries = [
        RpgMakerTextEntry(
            source_text=f"Line {index}",
            text_type=RpgMakerTextType.MESSAGE,
            origin=RpgMakerTextOrigin(
                file_name="Map001.json",
                origin_key=f"Map001.json|1|2|0|{index}|0",
                map_id=1,
                event_id=2,
                page_index=0,
                command_index=index,
                parameter_index=0,
            ),
        )
        for index in range(1, 5)
    ]

    repository.replace_project_entries(project, entries)

    page = repository.list_project_entries(project, limit=2, offset=1)

    assert [entry.source_text for entry in page] == ["Line 2", "Line 3"]
    assert repository.count_project_entries(project) == 4
    assert repository.get_entry(page[0].id) == page[0]


def test_rpg_maker_catalog_rejects_invalid_paging_arguments(
    connection_manager,
    tmp_path,
):
    repository = SQLiteRpgMakerTextCatalogRepository(connection_manager)
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=tmp_path / "Game" / "www" / "data",
        version=RpgMakerVersion.MZ,
    )

    with pytest.raises(ValueError, match="limit must be greater than zero"):
        repository.list_project_entries(project, limit=0)

    with pytest.raises(ValueError, match="offset must be zero or greater"):
        repository.list_project_entries(project, offset=-1)


def test_sqlite_connection_migrates_legacy_rpg_maker_catalog_columns(database_path):
    raw_connection = sqlite3.connect(str(database_path))
    try:
        raw_connection.executescript(
            """
            CREATE TABLE rpg_maker_text_catalog (
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
                created_at TEXT NOT NULL,
                UNIQUE(project_root, origin_key, normalized_source_text)
            );
            """
        )
        raw_connection.commit()
    finally:
        raw_connection.close()

    connection_manager = SQLiteConnectionManager(database_path)

    with connection_manager.open() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(rpg_maker_text_catalog)"
            ).fetchall()
        }

    assert "database_id" in columns
    assert "field_name" in columns


def test_catalog_translation_error_repository_replaces_last_batch_errors(
    connection_manager,
):
    repository = SQLiteCatalogTranslationErrorRepository(connection_manager)
    repository.save_error(
        CatalogTranslationError(
            entry_id=10,
            origin="Map001.json | ev 1",
            source_text="Hello",
            error_message="failed",
        )
    )

    errors = repository.list_last_batch_errors()

    assert len(errors) == 1
    assert errors[0].entry_id == 10
    assert errors[0].origin == "Map001.json | ev 1"
    assert errors[0].source_text == "Hello"
    assert errors[0].error_message == "failed"
    assert errors[0].created_at

    repository.clear_last_batch_errors()

    assert repository.list_last_batch_errors() == []
