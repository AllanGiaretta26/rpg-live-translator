from __future__ import annotations

from domain.interfaces import SettingsRepository

from .sqlite_connection import SQLiteConnectionManager


class SQLiteSettingsRepository(SettingsRepository):
    def __init__(self, database: SQLiteConnectionManager) -> None:
        self._database = database

    def get(self, key: str) -> str | None:
        normalized_key = key.strip()
        if not normalized_key:
            return None

        query = "SELECT value FROM settings WHERE key = ?"

        with self._database.open() as connection:
            row = connection.execute(query, (normalized_key,)).fetchone()

        if row is None:
            return None

        return row["value"]

    def set(self, key: str, value: str) -> None:
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("key must not be blank")

        statement = """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value
        """

        with self._database.open() as connection:
            connection.execute(statement, (normalized_key, value))

    def delete(self, key: str) -> None:
        normalized_key = key.strip()
        if not normalized_key:
            return

        with self._database.open() as connection:
            connection.execute("DELETE FROM settings WHERE key = ?", (normalized_key,))
