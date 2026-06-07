from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
import unicodedata

from live_translator.domain.interfaces import RpgMakerTextCatalog
from live_translator.domain.models import (
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextOrigin,
    RpgMakerTextType,
)

from .sqlite_connection import SQLiteConnectionManager


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip()
    normalized = " ".join(normalized.split())
    return normalized.casefold()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteRpgMakerTextCatalogRepository(RpgMakerTextCatalog):
    def __init__(self, database: SQLiteConnectionManager) -> None:
        self._database = database

    def replace_project_entries(
        self,
        project: RpgMakerProject,
        entries: Sequence[RpgMakerTextEntry],
    ) -> int:
        project_root = str(project.root_path)
        now = _utc_now()

        data_path = str(project.data_path)
        engine_version = project.version.value
        rows = []
        for entry in entries:
            normalized_text = _normalize_text(entry.source_text)
            if not normalized_text:
                continue
            rows.append(
                (
                    project_root,
                    data_path,
                    engine_version,
                    entry.source_text,
                    normalized_text,
                    entry.text_type.value,
                    entry.origin.file_name,
                    entry.origin.origin_key,
                    entry.origin.map_id,
                    entry.origin.event_id,
                    entry.origin.page_index,
                    entry.origin.command_index,
                    entry.origin.parameter_index,
                    entry.origin.database_id,
                    entry.origin.field_name,
                    now,
                )
            )

        with self._database.open() as connection:
            connection.execute(
                "DELETE FROM rpg_maker_text_catalog WHERE project_root = ?",
                (project_root,),
            )
            if rows:
                connection.executemany(
                    """
                    INSERT INTO rpg_maker_text_catalog (
                        project_root,
                        data_path,
                        engine_version,
                        source_text,
                        normalized_source_text,
                        text_type,
                        file_name,
                        origin_key,
                        map_id,
                        event_id,
                        page_index,
                        command_index,
                        parameter_index,
                        database_id,
                        field_name,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_root, origin_key, normalized_source_text)
                    DO UPDATE SET
                        source_text = excluded.source_text,
                        data_path = excluded.data_path,
                        engine_version = excluded.engine_version,
                        text_type = excluded.text_type,
                        file_name = excluded.file_name,
                        map_id = excluded.map_id,
                        event_id = excluded.event_id,
                        page_index = excluded.page_index,
                        command_index = excluded.command_index,
                        parameter_index = excluded.parameter_index,
                        database_id = excluded.database_id,
                        field_name = excluded.field_name
                    """,
                    rows,
                )

            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM rpg_maker_text_catalog
                WHERE project_root = ?
                """,
                (project_root,),
            ).fetchone()

        return int(row["count"])

    def count_project_entries(self, project: RpgMakerProject) -> int:
        with self._database.open() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM rpg_maker_text_catalog
                WHERE project_root = ?
                """,
                (str(project.root_path),),
            ).fetchone()
        return int(row["count"])

    def list_project_entries(
        self,
        project: RpgMakerProject,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RpgMakerTextEntry]:
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero")
        if offset < 0:
            raise ValueError("offset must be zero or greater")

        query = """
            SELECT *
            FROM rpg_maker_text_catalog
            WHERE project_root = ?
            ORDER BY
                file_name,
                event_id,
                page_index,
                command_index,
                parameter_index,
                database_id,
                field_name
            """
        parameters: list[object] = [str(project.root_path)]
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            parameters.extend([limit, offset])
        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            parameters.append(offset)

        with self._database.open() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [self._entry_from_row(row) for row in rows]

    def get_entry(self, entry_id: int) -> RpgMakerTextEntry | None:
        with self._database.open() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM rpg_maker_text_catalog
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()

        if row is None:
            return None
        return self._entry_from_row(row)

    def _entry_from_row(self, row) -> RpgMakerTextEntry:
        return RpgMakerTextEntry(
            id=int(row["id"]),
            source_text=row["source_text"],
            text_type=RpgMakerTextType(row["text_type"]),
            origin=RpgMakerTextOrigin(
                file_name=row["file_name"],
                origin_key=row["origin_key"],
                map_id=row["map_id"],
                event_id=row["event_id"],
                page_index=row["page_index"],
                command_index=row["command_index"],
                parameter_index=row["parameter_index"],
                database_id=row["database_id"],
                field_name=row["field_name"],
            ),
        )
