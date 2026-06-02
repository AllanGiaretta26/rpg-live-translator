from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from live_translator.domain.interfaces import RpgMakerTextParser
from live_translator.domain.models import (
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextOrigin,
    RpgMakerTextType,
)


_MAP_FILE_PATTERN = re.compile(r"Map(\d+)\.json$")
_TACHIE_SHOW_NAME_PATTERN = re.compile(r"^Tachie\s+showName\s+(?P<name>.+?)\s*$")


class RpgMakerJsonParseError(ValueError):
    """Raised when an RPG Maker JSON file cannot be read."""


class RpgMakerJsonTextParser(RpgMakerTextParser):
    def parse_project(self, project: RpgMakerProject) -> list[RpgMakerTextEntry]:
        entries: list[RpgMakerTextEntry] = []
        entries.extend(
            self._parse_common_events(project.data_path / "CommonEvents.json")
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Items.json",
                field_types={
                    "name": RpgMakerTextType.ITEM_NAME,
                    "description": RpgMakerTextType.ITEM_DESCRIPTION,
                },
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Skills.json",
                field_types={
                    "name": RpgMakerTextType.SKILL_NAME,
                    "description": RpgMakerTextType.SKILL_DESCRIPTION,
                    "message1": RpgMakerTextType.SKILL_MESSAGE,
                    "message2": RpgMakerTextType.SKILL_MESSAGE,
                },
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Weapons.json",
                field_types={
                    "name": RpgMakerTextType.WEAPON_NAME,
                    "description": RpgMakerTextType.WEAPON_DESCRIPTION,
                },
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Armors.json",
                field_types={
                    "name": RpgMakerTextType.ARMOR_NAME,
                    "description": RpgMakerTextType.ARMOR_DESCRIPTION,
                },
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "States.json",
                field_types={
                    "name": RpgMakerTextType.STATE_NAME,
                    "message1": RpgMakerTextType.STATE_MESSAGE,
                    "message2": RpgMakerTextType.STATE_MESSAGE,
                    "message3": RpgMakerTextType.STATE_MESSAGE,
                    "message4": RpgMakerTextType.STATE_MESSAGE,
                },
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Classes.json",
                field_types={"name": RpgMakerTextType.CLASS_NAME},
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Enemies.json",
                field_types={"name": RpgMakerTextType.ENEMY_NAME},
            )
        )
        entries.extend(
            self._parse_database_file(
                project.data_path / "Actors.json",
                field_types={"name": RpgMakerTextType.ACTOR_NAME},
            )
        )
        entries.extend(self._parse_system_terms(project.data_path / "System.json"))
        entries.extend(self._parse_troops(project.data_path / "Troops.json"))
        entries.extend(self._parse_scenario(project.data_path / "Scenario.json"))

        for path in sorted(project.data_path.glob("Map*.json")):
            if _MAP_FILE_PATTERN.match(path.name):
                entries.extend(self._parse_map(path))

        return entries

    def _parse_scenario(self, path: Path) -> list[RpgMakerTextEntry]:
        if not path.exists():
            return []

        data = self._read_json(path)
        if not isinstance(data, dict):
            return []

        entries: list[RpgMakerTextEntry] = []
        for scenario_key, commands in data.items():
            if not isinstance(scenario_key, str) or not isinstance(commands, list):
                continue
            entries.extend(
                self._entries_from_commands(
                    file_name=path.name,
                    commands=commands,
                    field_name=scenario_key,
                )
            )
        return entries

    def _parse_database_file(
        self,
        path: Path,
        *,
        field_types: Mapping[str, RpgMakerTextType],
    ) -> list[RpgMakerTextEntry]:
        if not path.exists():
            return []

        data = self._read_json(path)
        if not isinstance(data, list):
            return []

        entries: list[RpgMakerTextEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            database_id = self._optional_int(item.get("id"))
            if database_id is None:
                continue

            for field_name, text_type in field_types.items():
                entries.extend(
                    self._database_entries_for_field(
                        file_name=path.name,
                        database_id=database_id,
                        field_name=field_name,
                        text_type=text_type,
                        value=item.get(field_name),
                    )
                )
        return entries

    def _parse_system_terms(self, path: Path) -> list[RpgMakerTextEntry]:
        if not path.exists():
            return []

        data = self._read_json(path)
        if not isinstance(data, dict):
            return []

        terms = data.get("terms")
        entries: list[RpgMakerTextEntry] = []
        self._extend_system_term_entries(
            entries,
            file_name=path.name,
            path_parts=("terms",),
            value=terms,
        )
        return entries

    def _parse_common_events(self, path: Path) -> list[RpgMakerTextEntry]:
        if not path.exists():
            return []

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

    def _parse_troops(self, path: Path) -> list[RpgMakerTextEntry]:
        if not path.exists():
            return []

        data = self._read_json(path)
        if not isinstance(data, list):
            return []

        entries: list[RpgMakerTextEntry] = []
        for troop in data:
            if not isinstance(troop, dict):
                continue

            troop_id = self._optional_int(troop.get("id"))
            if troop_id is None:
                continue

            pages = troop.get("pages")
            if not isinstance(pages, list):
                continue

            for page_index, page in enumerate(pages):
                if not isinstance(page, dict):
                    continue
                commands = page.get("list")
                if not isinstance(commands, list):
                    continue
                entries.extend(
                    self._entries_from_commands(
                        file_name=path.name,
                        commands=commands,
                        page_index=page_index,
                        database_id=troop_id,
                        speaker_type=RpgMakerTextType.TROOP_SPEAKER,
                        message_type=RpgMakerTextType.TROOP_MESSAGE,
                        choice_type=RpgMakerTextType.TROOP_CHOICE,
                        scrolling_text_type=RpgMakerTextType.TROOP_SCROLLING_TEXT,
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
        database_id: int | None = None,
        field_name: str | None = None,
        speaker_type: RpgMakerTextType = RpgMakerTextType.SPEAKER,
        message_type: RpgMakerTextType = RpgMakerTextType.MESSAGE,
        choice_type: RpgMakerTextType = RpgMakerTextType.CHOICE,
        scrolling_text_type: RpgMakerTextType = RpgMakerTextType.SCROLLING_TEXT,
    ) -> list[RpgMakerTextEntry]:
        entries: list[RpgMakerTextEntry] = []
        command_index = 0
        while command_index < len(commands):
            command = commands[command_index]
            if not isinstance(command, dict):
                command_index += 1
                continue

            code = command.get("code")
            parameters = command.get("parameters")
            if not isinstance(parameters, list):
                parameters = []

            if code == 101:
                entries.extend(
                    self._speaker_entry(
                        text_type=speaker_type,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
                        command_index=command_index,
                    )
                )
            elif code == 356:
                entries.extend(
                    self._tachie_speaker_entry(
                        text_type=speaker_type,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
                        command_index=command_index,
                    )
                )
            elif code == 401:
                entries.extend(
                    self._grouped_text_entry(
                        text_type=message_type,
                        file_name=file_name,
                        commands=commands,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
                        start_index=command_index,
                        code=401,
                    )
                )
                command_index = self._next_non_matching_command(
                    commands,
                    command_index,
                    401,
                )
                continue
            elif code == 102:
                entries.extend(
                    self._choice_entries(
                        text_type=choice_type,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
                        command_index=command_index,
                    )
                )
            elif code == 402:
                entries.extend(
                    self._single_text_entry(
                        text_type=choice_type,
                        parameter_index=1,
                        file_name=file_name,
                        parameters=parameters,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
                        command_index=command_index,
                    )
                )
            elif code == 405:
                entries.extend(
                    self._grouped_text_entry(
                        text_type=scrolling_text_type,
                        file_name=file_name,
                        commands=commands,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
                        start_index=command_index,
                        code=405,
                    )
                )
                command_index = self._next_non_matching_command(
                    commands,
                    command_index,
                    405,
                )
                continue
            command_index += 1
        return entries

    def _grouped_text_entry(
        self,
        *,
        text_type: RpgMakerTextType,
        file_name: str,
        commands: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        database_id: int | None,
        field_name: str | None,
        start_index: int,
        code: int,
    ) -> list[RpgMakerTextEntry]:
        lines: list[str] = []
        command_index = start_index
        while command_index < len(commands):
            command = commands[command_index]
            if not isinstance(command, dict) or command.get("code") != code:
                break

            parameters = command.get("parameters")
            if isinstance(parameters, list) and parameters:
                text = parameters[0]
                if isinstance(text, str) and text.strip():
                    lines.append(text)
            command_index += 1

        if not lines:
            return []

        return [
            self._entry(
                text="\n".join(lines),
                text_type=text_type,
                file_name=file_name,
                map_id=map_id,
                event_id=event_id,
                page_index=page_index,
                database_id=database_id,
                field_name=field_name,
                command_index=start_index,
                parameter_index=0,
            )
        ]

    def _next_non_matching_command(
        self,
        commands: list[Any],
        start_index: int,
        code: int,
    ) -> int:
        command_index = start_index
        while command_index < len(commands):
            command = commands[command_index]
            if not isinstance(command, dict) or command.get("code") != code:
                break
            command_index += 1
        return command_index

    def _speaker_entry(
        self,
        *,
        text_type: RpgMakerTextType,
        file_name: str,
        parameters: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        database_id: int | None,
        field_name: str | None,
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
                text_type=text_type,
                file_name=file_name,
                map_id=map_id,
                event_id=event_id,
                page_index=page_index,
                database_id=database_id,
                field_name=field_name,
                command_index=command_index,
                parameter_index=4,
            )
        ]

    def _tachie_speaker_entry(
        self,
        *,
        text_type: RpgMakerTextType,
        file_name: str,
        parameters: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        database_id: int | None,
        field_name: str | None,
        command_index: int,
    ) -> list[RpgMakerTextEntry]:
        if not parameters or not isinstance(parameters[0], str):
            return []

        match = _TACHIE_SHOW_NAME_PATTERN.match(parameters[0])
        if match is None:
            return []

        text = match.group("name").strip()
        if not _is_translatable_tachie_name(text):
            return []

        return [
            self._entry(
                text=text,
                text_type=text_type,
                file_name=file_name,
                map_id=map_id,
                event_id=event_id,
                page_index=page_index,
                database_id=database_id,
                field_name=field_name,
                command_index=command_index,
                parameter_index=0,
            )
        ]

    def _choice_entries(
        self,
        *,
        text_type: RpgMakerTextType,
        file_name: str,
        parameters: list[Any],
        map_id: int | None,
        event_id: int | None,
        page_index: int | None,
        database_id: int | None,
        field_name: str | None,
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
                        text_type=text_type,
                        file_name=file_name,
                        map_id=map_id,
                        event_id=event_id,
                        page_index=page_index,
                        database_id=database_id,
                        field_name=field_name,
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
        database_id: int | None,
        field_name: str | None,
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
                database_id=database_id,
                field_name=field_name,
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
        database_id: int | None,
        field_name: str | None = None,
        command_index: int,
        parameter_index: int,
    ) -> RpgMakerTextEntry:
        if field_name is not None:
            origin_key = "|".join(
                (
                    file_name,
                    "scenario",
                    field_name,
                    str(command_index),
                    str(parameter_index),
                )
            )
        elif database_id is None:
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
        else:
            origin_key = "|".join(
                (
                    file_name,
                    "database",
                    str(database_id),
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
                database_id=database_id,
                field_name=field_name,
            ),
        )

    def _database_entries_for_field(
        self,
        *,
        file_name: str,
        database_id: int,
        field_name: str,
        text_type: RpgMakerTextType,
        value: Any,
    ) -> list[RpgMakerTextEntry]:
        if not isinstance(value, str) or not value.strip():
            return []

        return [
            RpgMakerTextEntry(
                source_text=value,
                text_type=text_type,
                origin=RpgMakerTextOrigin(
                    file_name=file_name,
                    origin_key=f"{file_name}|database|{database_id}|{field_name}",
                    database_id=database_id,
                    field_name=field_name,
                ),
            )
        ]

    def _extend_system_term_entries(
        self,
        entries: list[RpgMakerTextEntry],
        *,
        file_name: str,
        path_parts: tuple[str, ...],
        value: Any,
    ) -> None:
        if isinstance(value, str):
            if not value.strip():
                return
            field_name = ".".join(path_parts)
            entries.append(
                RpgMakerTextEntry(
                    source_text=value,
                    text_type=RpgMakerTextType.SYSTEM_TERM,
                    origin=RpgMakerTextOrigin(
                        file_name=file_name,
                        origin_key=f"{file_name}|system|{field_name}",
                        field_name=field_name,
                    ),
                )
            )
            return

        if isinstance(value, list):
            for index, item in enumerate(value):
                self._extend_system_term_entries(
                    entries,
                    file_name=file_name,
                    path_parts=(*path_parts, str(index)),
                    value=item,
                )
            return

        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    continue
                self._extend_system_term_entries(
                    entries,
                    file_name=file_name,
                    path_parts=(*path_parts, key),
                    value=item,
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


def _is_translatable_tachie_name(text: str) -> bool:
    if not text.strip() or text.lstrip().startswith("\\"):
        return False
    if text.strip() in {"?", "??", "???", "？", "？？", "？？？"}:
        return False
    return any(character.isalnum() for character in text)
