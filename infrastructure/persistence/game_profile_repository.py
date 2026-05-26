from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from domain.interfaces import GameProfileRepository, SettingsRepository
from domain.models import GameProfile, TextRegion

from .settings_repository import SQLiteSettingsRepository
from .sqlite_connection import SQLiteConnectionManager


ACTIVE_PROFILE_SETTING_KEY = "active_game_profile_name"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteGameProfileRepository(GameProfileRepository):
    def __init__(
        self,
        database: SQLiteConnectionManager,
        settings_repository: SettingsRepository | None = None,
    ) -> None:
        self._database = database
        self._settings_repository = settings_repository or SQLiteSettingsRepository(database)

    def get_active_profile(self) -> GameProfile | None:
        active_profile_name = self._settings_repository.get(ACTIVE_PROFILE_SETTING_KEY)

        if active_profile_name:
            profile = self._get_by_name(active_profile_name)
            if profile is not None:
                return profile

        query = """
        SELECT name, window_title, region_x, region_y, region_width, region_height
        FROM game_profiles
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """

        with self._database.open() as connection:
            row = connection.execute(query).fetchone()

        if row is None:
            return None

        return self._row_to_profile(row)

    def save(self, profile: GameProfile) -> None:
        statement = """
        INSERT INTO game_profiles (
            name,
            window_title,
            region_x,
            region_y,
            region_width,
            region_height,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            window_title = excluded.window_title,
            region_x = excluded.region_x,
            region_y = excluded.region_y,
            region_width = excluded.region_width,
            region_height = excluded.region_height,
            updated_at = excluded.updated_at
        """

        timestamp = _utc_now()

        with self._database.open() as connection:
            connection.execute(
                statement,
                (
                    profile.name,
                    profile.window_title,
                    profile.text_region.x,
                    profile.text_region.y,
                    profile.text_region.width,
                    profile.text_region.height,
                    timestamp,
                    timestamp,
                ),
            )

        self._settings_repository.set(ACTIVE_PROFILE_SETTING_KEY, profile.name)

    def _get_by_name(self, name: str) -> GameProfile | None:
        query = """
        SELECT name, window_title, region_x, region_y, region_width, region_height
        FROM game_profiles
        WHERE name = ?
        """

        with self._database.open() as connection:
            row = connection.execute(query, (name,)).fetchone()

        if row is None:
            return None

        return self._row_to_profile(row)

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> GameProfile:
        return GameProfile(
            name=row["name"],
            window_title=row["window_title"],
            text_region=TextRegion(
                x=row["region_x"],
                y=row["region_y"],
                width=row["region_width"],
                height=row["region_height"],
            ),
        )
