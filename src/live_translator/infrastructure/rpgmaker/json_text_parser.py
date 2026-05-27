from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from live_translator.domain.interfaces import RpgMakerTextParser
from live_translator.domain.models import (
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextOrigin,
    RpgMakerTextType,
)


_MAP_FILE_PATTERN = re.compile(r"Map(\d+)\.json$")


class RpgMakerJsonParseError(ValueError):
    """Raised when an RPG Maker JSON file cannot be read."""


class RpgMakerJsonTextParser(RpgMakerTextParser):
    def parse_project(self, project: RpgMakerProject) -> list[RpgMakerTextEntry]:
        entries: list[RpgMakerTextEntry] = []
        entries.extend(self._parse_common_events(project.data_path / "CommonEvents.json"))

        for path in sorted(project.data_path.glob("Map*.json")):
            if _MAP_FILE_PATTERN.match(path.name):
                entries.extend(self._parse_map(path))

        return entries

    def _parse_common_events(self, path: Path) -> list[RpgMakerTextEntry]:
        data = self._read_json(path)
        if not isinstance(data, list):
            return []

        entries: list[RpgMakerTextEntry] = []
        for event in data:
            if not isinstance(event, dict):
                continue

            event_id = self._optional_int(event.get("id"))
            commands = event.get("list")
            if isinstance(commands, list):
                entries.extend(
                    self._entries_from_commands(
                        file_name=path.name,
                        commands=commands,
                        event_id=event_id,
                    )
                )
        return entries

    def _parse_map(self, path: Path) -> list[RpgMakerTextEntry]:
        data = self._read_json(path)
        if not isinstance(data, dict):
            return []

        map_match = _MAP_FILE_PATTERN.match(path.name)
        map_id = int(map_match.group(1)) if map_match else None
        events = data.get("events")
        if isinstance(events, dict):
            iterable_events: Iterable[Any] = events.values()
        elif isinstance(events, list):
            iterable_events = events
        else:
            iterable_events = []

        entries: list[RpgMakerTextEntry] = []
        for event in iterable_events:
            if not isinstance(event, dict):
                continue

            event_id = self._optional_int(event.get("id"))
            pages = event.get("pages")
            if not isinstance(pages, list):
                continue

            for page_index, page in enumerate(pages):
                if not isinstance(page, dict):
                    continue

                commands = page.get("list")
                if isinstance(commands, list):
                    entries.extend(
                        self._entries_from_commands(
                            file_name=path.name,
                            commands=commands,
                            map_id=map_id,
                            event_id=event_id,
                            page_index=page_index,
                        )
                    )
        return entries

    def _entries_from_commands(
        self,
        *,
        file_name: str,
        commands: list[Any],
        map_id: int | None = None,
        event_id: int | None = None,
        page_index: int | None = None,
    ) -> list[RpgMakerTextEntry]:
        entries: list[RpgMakerTextEntry] = []
        for command_index, command in enumerate(commands):
            if not isinstance(command, dict):
                continue

            code = command.get("code")
            parameters = command.get("parameters")
            if not isinstance(parameters, list):
                parameters = []

            if code == 101:
                entries.extend(
                    self._speaker_entry(
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        command_index=command_index,
                    )
                )
            elif code == 401:
                entries.extend(
                    self._single_text_entry(
                        text_type=RpgMakerTextType.MESSAGE,
                        parameter_index=0,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        command_index=command_index,
                    )
                )
            elif code == 102:
                entries.extend(
                    self._choice_entries(
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        command_index=command_index,
                    )
                )
            elif code == 402:
                entries.extend(
                    self._single_text_entry(
                        text_type=RpgMakerTextType.CHOICE,
                        parameter_index=1,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        command_index=command_index,
                    )
                )
            elif code == 405:
                entries.extend(
                    self._single_text_entry(
                        text_type=RpgMakerTextType.SCROLLING_TEXT,
                        parameter_index=0,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        command_index=command_index,
                    )
                )
        return entries

    def _speaker_entry(
        self,
        *,
        file_name: str,
        parameters: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        command_index: int,
    ) -> list[RpgMakerTextEntry]:
        if len(parameters) <= 4:
            return []

        text = parameters[4]
        if not isinstance(text, str) or not text.strip():
            return []

        return [
            self._entry(
                text=text,
                text_type=RpgMakerTextType.SPEAKER,
                file_name=file_name,
                map_id=map_id,
                event_id=event_id,
                page_index=page_index,
                command_index=command_index,
                parameter_index=4,
            )
        ]

    def _choice_entries(
        self,
        *,
        file_name: str,
        parameters: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        command_index: int,
    ) -> list[RpgMakerTextEntry]:
        if not parameters or not isinstance(parameters[0], list):
            return []

        entries: list[RpgMakerTextEntry] = []
        for choice_index, choice in enumerate(parameters[0]):
            if isinstance(choice, str) and choice.strip():
                entries.append(
                    self._entry(
                        text=choice,
                        text_type=RpgMakerTextType.CHOICE,
                        file_name=file_name,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        command_index=command_index,
                        parameter_index=choice_index,
                    )
                )
        return entries

    def _single_text_entry(
        self,
        *,
        text_type: RpgMakerTextType,
        parameter_index: int,
        file_name: str,
        parameters: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        command_index: int,
    ) -> list[RpgMakerTextEntry]:
        if len(parameters) <= parameter_index:
            return []

        text = parameters[parameter_index]
        if not isinstance(text, str) or not text.strip():
            return []

        return [
            self._entry(
                text=text,
                text_type=text_type,
                file_name=file_name,
                map_id=map_id,
                event_id=event_id,
                page_index=page_index,
                command_index=command_index,
                parameter_index=parameter_index,
            )
        ]

    def _entry(
        self,
        *,
        text: str,
        text_type: RpgMakerTextType,
        file_name: str,
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        command_index: int,
        parameter_index: int,
    ) -> RpgMakerTextEntry:
        origin_key = "|".join(
            (
                file_name,
                str(map_id) if map_id is not None else "",
                str(event_id) if event_id is not None else "",
                str(page_index) if page_index is not None else "",
                str(command_index),
                str(parameter_index),
            )
        )
        return RpgMakerTextEntry(
            source_text=text,
            text_type=text_type,
            origin=RpgMakerTextOrigin(
                file_name=file_name,
                origin_key=origin_key,
                map_id=map_id,
                event_id=event_id,
                page_index=page_index,
                command_index=command_index,
                parameter_index=parameter_index,
            ),
        )

    def _read_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except OSError as error:
            raise RpgMakerJsonParseError(f"nao foi possivel ler {path}") from error
        except json.JSONDecodeError as error:
            raise RpgMakerJsonParseError(f"json invalido em {path}") from error

    def _optional_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdecimal():
            return int(value)
        return None
