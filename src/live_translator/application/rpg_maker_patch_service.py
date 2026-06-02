from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import textwrap
from typing import Any, Iterable

from live_translator.application.translation_quality import (
    RPG_MAKER_DESCRIPTION_LINE_LIMIT,
    looks_like_invalid_translation,
)
from live_translator.domain.interfaces import TranslationCache
from live_translator.domain.models import (
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextType,
)


PATCH_REPORT_JSON = "live-translator-patch-report.json"
PATCH_REPORT_MD = "live-translator-patch-report.md"
BACKUP_MANIFEST = "live-translator-backup.json"
_TACHIE_SHOW_NAME_PATTERN = re.compile(
    r"^(?P<prefix>Tachie\s+showName\s+)(?P<name>.+?)(?P<suffix>\s*)$"
)


@dataclass(frozen=True, slots=True)
class RpgMakerPatchResult:
    patch_path: Path
    data_path: Path
    report_path: Path
    summary_path: Path
    total_entries: int
    applied_entries: int
    missing_cache: int
    invalid_translations: int
    source_mismatches: int
    skipped_speakers: int
    files_written: int


@dataclass(frozen=True, slots=True)
class RpgMakerPatchApplyResult:
    patch_path: Path
    backup_path: Path
    files_applied: int


@dataclass(frozen=True, slots=True)
class RpgMakerPatchRestoreResult:
    backup_path: Path
    files_restored: int


@dataclass(frozen=True, slots=True)
class _PatchPlanEntry:
    entry: RpgMakerTextEntry
    translated_text: str


class RpgMakerPatchService:
    def __init__(
        self,
        translation_cache: TranslationCache,
        *,
        cache_scope: str | None = None,
        export_root: Path = Path("exports") / "patches",
        backup_root: Path = Path("backups") / "patches",
    ) -> None:
        self._translation_cache = translation_cache
        self._cache_scope = cache_scope
        self._export_root = export_root
        self._backup_root = backup_root

    def export_patch(
        self,
        *,
        project: RpgMakerProject,
        entries: Iterable[RpgMakerTextEntry],
        include_speakers: bool = False,
    ) -> RpgMakerPatchResult:
        timestamp = _timestamp()
        patch_path = self._export_root / f"{project.root_path.name}-ptBR-{timestamp}"
        patch_data_path = patch_path / "data"
        patch_data_path.mkdir(parents=True, exist_ok=True)

        plan_entries: list[_PatchPlanEntry] = []
        skipped: list[dict[str, object]] = []
        counts = {
            "total_entries": 0,
            "missing_cache": 0,
            "invalid_translations": 0,
            "source_mismatches": 0,
            "skipped_speakers": 0,
        }

        for entry in entries:
            if entry.text_type not in _PATCHABLE_TEXT_TYPES:
                continue
            counts["total_entries"] += 1
            if entry.text_type == RpgMakerTextType.SPEAKER and not include_speakers:
                counts["skipped_speakers"] += 1
                skipped.append(_skipped_entry(entry, "speaker disabled"))
                continue

            cached = self._translation_cache.get_by_text(
                entry.source_text,
                scope=self._cache_scope,
            )
            if cached is None:
                counts["missing_cache"] += 1
                skipped.append(_skipped_entry(entry, "missing cache"))
                continue
            if looks_like_invalid_translation(
                entry.source_text,
                cached.translated_text,
                text_type=entry.text_type,
            ):
                counts["invalid_translations"] += 1
                skipped.append(_skipped_entry(entry, "invalid translation"))
                continue
            plan_entries.append(
                _PatchPlanEntry(entry=entry, translated_text=cached.translated_text)
            )

        applied_entries = 0
        files_written = 0
        changed_files: list[str] = []
        file_entries = _entries_by_file(plan_entries)
        for file_name, entries_for_file in file_entries.items():
            source_path = project.data_path / file_name
            try:
                data = _read_json(source_path)
            except (OSError, json.JSONDecodeError) as error:
                for plan_entry in entries_for_file:
                    counts["source_mismatches"] += 1
                    skipped.append(_skipped_entry(plan_entry.entry, str(error)))
                continue

            original_data = deepcopy(data)
            for plan_entry in sorted(
                entries_for_file,
                key=_descending_origin_sort_key,
                reverse=True,
            ):
                result = _apply_entry_to_data(data, plan_entry)
                if result is None:
                    counts["source_mismatches"] += 1
                    skipped.append(_skipped_entry(plan_entry.entry, "source mismatch"))
                    continue
                applied_entries += 1

            if data != original_data:
                target_path = patch_data_path / file_name
                _write_json(target_path, data)
                changed_files.append(file_name)
                files_written += 1

        report = {
            "project_root": str(project.root_path),
            "data_path": str(project.data_path),
            "include_speakers": include_speakers,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "patch_data_path": str(patch_data_path),
            "total_entries": counts["total_entries"],
            "applied_entries": applied_entries,
            "missing_cache": counts["missing_cache"],
            "invalid_translations": counts["invalid_translations"],
            "source_mismatches": counts["source_mismatches"],
            "skipped_speakers": counts["skipped_speakers"],
            "files_written": files_written,
            "changed_files": changed_files,
            "skipped": skipped,
        }
        report_path = patch_path / PATCH_REPORT_JSON
        summary_path = patch_path / PATCH_REPORT_MD
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary_path.write_text(_build_markdown_report(report), encoding="utf-8")

        return RpgMakerPatchResult(
            patch_path=patch_path,
            data_path=patch_data_path,
            report_path=report_path,
            summary_path=summary_path,
            total_entries=int(counts["total_entries"]),
            applied_entries=applied_entries,
            missing_cache=int(counts["missing_cache"]),
            invalid_translations=int(counts["invalid_translations"]),
            source_mismatches=int(counts["source_mismatches"]),
            skipped_speakers=int(counts["skipped_speakers"]),
            files_written=files_written,
        )

    def apply_patch(
        self,
        *,
        project: RpgMakerProject,
        patch_path: Path,
    ) -> RpgMakerPatchApplyResult:
        patch_data_path = patch_path / "data"
        if not patch_data_path.is_dir():
            raise FileNotFoundError(f"patch data not found: {patch_data_path}")

        patch_files = sorted(path for path in patch_data_path.glob("*.json"))
        if not patch_files:
            raise ValueError("patch has no JSON files to apply")

        timestamp = _timestamp()
        backup_path = self._backup_root / f"{project.root_path.name}-{timestamp}"
        backup_data_path = backup_path / "data"
        backup_data_path.mkdir(parents=True, exist_ok=True)

        files_applied = 0
        backed_up_files: list[str] = []
        for patch_file in patch_files:
            target_file = project.data_path / patch_file.name
            if target_file.exists():
                shutil.copy2(target_file, backup_data_path / patch_file.name)
                backed_up_files.append(patch_file.name)
            shutil.copy2(patch_file, target_file)
            files_applied += 1

        manifest = {
            "project_root": str(project.root_path),
            "data_path": str(project.data_path),
            "patch_path": str(patch_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": backed_up_files,
        }
        (backup_path / BACKUP_MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return RpgMakerPatchApplyResult(
            patch_path=patch_path,
            backup_path=backup_path,
            files_applied=files_applied,
        )

    def restore_latest_backup(
        self,
        *,
        project: RpgMakerProject,
    ) -> RpgMakerPatchRestoreResult:
        backup_path = self._latest_backup_path(project)
        if backup_path is None:
            raise FileNotFoundError("no patch backup found for active project")

        backup_data_path = backup_path / "data"
        if not backup_data_path.is_dir():
            raise FileNotFoundError(f"backup data not found: {backup_data_path}")

        restored = 0
        for backup_file in sorted(backup_data_path.glob("*.json")):
            shutil.copy2(backup_file, project.data_path / backup_file.name)
            restored += 1

        return RpgMakerPatchRestoreResult(
            backup_path=backup_path,
            files_restored=restored,
        )

    def _latest_backup_path(self, project: RpgMakerProject) -> Path | None:
        candidates: list[tuple[str, Path]] = []
        for manifest_path in self._backup_root.glob(f"*/{BACKUP_MANIFEST}"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if manifest.get("project_root") != str(project.root_path):
                continue
            created_at = str(manifest.get("created_at") or "")
            candidates.append((created_at, manifest_path.parent))

        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item[0])[-1][1]


_PATCHABLE_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.MESSAGE,
        RpgMakerTextType.CHOICE,
        RpgMakerTextType.SCROLLING_TEXT,
        RpgMakerTextType.SPEAKER,
        RpgMakerTextType.ITEM_NAME,
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_NAME,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.SKILL_MESSAGE,
        RpgMakerTextType.WEAPON_NAME,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_NAME,
        RpgMakerTextType.ARMOR_DESCRIPTION,
        RpgMakerTextType.STATE_NAME,
        RpgMakerTextType.STATE_MESSAGE,
        RpgMakerTextType.CLASS_NAME,
        RpgMakerTextType.ENEMY_NAME,
        RpgMakerTextType.ACTOR_NAME,
        RpgMakerTextType.SYSTEM_TERM,
        RpgMakerTextType.TROOP_MESSAGE,
        RpgMakerTextType.TROOP_CHOICE,
        RpgMakerTextType.TROOP_SCROLLING_TEXT,
        RpgMakerTextType.TROOP_SPEAKER,
    }
)

MESSAGE_LINE_LIMIT = 58
MESSAGE_SHORT_LINE_REFLOW_LIMIT = 18


def _entries_by_file(
    entries: Iterable[_PatchPlanEntry],
) -> dict[str, list[_PatchPlanEntry]]:
    result: dict[str, list[_PatchPlanEntry]] = {}
    for entry in entries:
        result.setdefault(entry.entry.origin.file_name, []).append(entry)
    return result


def _descending_origin_sort_key(plan_entry: _PatchPlanEntry) -> tuple[int, int, int]:
    origin = plan_entry.entry.origin
    return (
        origin.event_id or -1,
        origin.page_index or -1,
        origin.command_index or -1,
    )


def _apply_entry_to_data(data: Any, plan_entry: _PatchPlanEntry) -> bool | None:
    entry = plan_entry.entry
    if entry.text_type in _DATABASE_TEXT_TYPES:
        return _replace_database_field(data, entry, plan_entry.translated_text)
    if entry.text_type == RpgMakerTextType.SYSTEM_TERM:
        return _replace_system_term(data, entry, plan_entry.translated_text)

    command_list = _command_list_for_entry(data, entry)
    if command_list is None or entry.origin.command_index is None:
        return None
    command_index = entry.origin.command_index
    if command_index < 0 or command_index >= len(command_list):
        return None

    command = command_list[command_index]
    if not isinstance(command, dict):
        return None

    if entry.text_type in _MESSAGE_TEXT_TYPES:
        return _replace_grouped_commands(
            command_list,
            command_index,
            code=401,
            source_text=entry.source_text,
            translated_text=plan_entry.translated_text,
            line_limit=MESSAGE_LINE_LIMIT,
            reflow_short_lines=True,
        )
    if entry.text_type in _SCROLLING_TEXT_TYPES:
        return _replace_grouped_commands(
            command_list,
            command_index,
            code=405,
            source_text=entry.source_text,
            translated_text=plan_entry.translated_text,
            line_limit=MESSAGE_LINE_LIMIT,
            reflow_short_lines=False,
        )
    if entry.text_type in _CHOICE_TEXT_TYPES:
        return _replace_choice(command, entry, plan_entry.translated_text)
    if entry.text_type in _SPEAKER_TEXT_TYPES:
        return _replace_speaker(command, entry, plan_entry.translated_text)
    return None


_DATABASE_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_NAME,
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_NAME,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.SKILL_MESSAGE,
        RpgMakerTextType.WEAPON_NAME,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_NAME,
        RpgMakerTextType.ARMOR_DESCRIPTION,
        RpgMakerTextType.STATE_NAME,
        RpgMakerTextType.STATE_MESSAGE,
        RpgMakerTextType.CLASS_NAME,
        RpgMakerTextType.ENEMY_NAME,
        RpgMakerTextType.ACTOR_NAME,
    }
)

_MESSAGE_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.MESSAGE,
        RpgMakerTextType.TROOP_MESSAGE,
    }
)
_CHOICE_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.CHOICE,
        RpgMakerTextType.TROOP_CHOICE,
    }
)
_SCROLLING_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.SCROLLING_TEXT,
        RpgMakerTextType.TROOP_SCROLLING_TEXT,
    }
)
_SPEAKER_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.SPEAKER,
        RpgMakerTextType.TROOP_SPEAKER,
    }
)
_DESCRIPTION_TEXT_TYPES = frozenset(
    {
        RpgMakerTextType.ITEM_DESCRIPTION,
        RpgMakerTextType.SKILL_DESCRIPTION,
        RpgMakerTextType.WEAPON_DESCRIPTION,
        RpgMakerTextType.ARMOR_DESCRIPTION,
    }
)


def _replace_database_field(
    data: Any,
    entry: RpgMakerTextEntry,
    translated_text: str,
) -> bool | None:
    if not isinstance(data, list):
        return None

    database_id = entry.origin.database_id
    field_name = entry.origin.field_name
    if database_id is None or field_name is None:
        return None

    for item in data:
        if not isinstance(item, dict) or not _database_id_matches(
            item.get("id"),
            database_id,
        ):
            continue
        if item.get(field_name) != entry.source_text:
            return None
        item[field_name] = _database_replacement_text(entry.text_type, translated_text)
        return True
    return None


def _database_replacement_text(
    text_type: RpgMakerTextType,
    translated_text: str,
) -> str:
    if text_type not in _DESCRIPTION_TEXT_TYPES:
        return translated_text
    return "\n".join(
        _wrapped_translation_lines(
            translated_text,
            width=RPG_MAKER_DESCRIPTION_LINE_LIMIT,
            normalize_lines=True,
        )
    )


def _database_id_matches(value: Any, database_id: int) -> bool:
    if value == database_id:
        return True
    if isinstance(value, str) and value.isdecimal():
        return int(value) == database_id
    return False


def _database_item_by_id(data: Iterable[Any], database_id: int) -> Any | None:
    for item in data:
        if isinstance(item, dict) and _database_id_matches(item.get("id"), database_id):
            return item
    return None


def _replace_system_term(
    data: Any,
    entry: RpgMakerTextEntry,
    translated_text: str,
) -> bool | None:
    field_name = entry.origin.field_name
    if not isinstance(data, dict) or field_name is None:
        return None
    return _replace_path_value(
        data,
        field_name.split("."),
        entry.source_text,
        translated_text,
    )


def _replace_path_value(
    data: Any,
    path_parts: list[str],
    source_text: str,
    translated_text: str,
) -> bool | None:
    if not path_parts:
        return None

    current = data
    for path_part in path_parts[:-1]:
        current = _path_child(current, path_part)
        if current is None:
            return None

    final_part = path_parts[-1]
    if isinstance(current, dict):
        if current.get(final_part) != source_text:
            return None
        current[final_part] = translated_text
        return True

    if isinstance(current, list) and final_part.isdecimal():
        index = int(final_part)
        if index < 0 or index >= len(current) or current[index] != source_text:
            return None
        current[index] = translated_text
        return True

    return None


def _path_child(value: Any, path_part: str) -> Any | None:
    if isinstance(value, dict):
        return value.get(path_part)
    if isinstance(value, list) and path_part.isdecimal():
        index = int(path_part)
        if 0 <= index < len(value):
            return value[index]
    return None


def _command_list_for_entry(
    data: Any,
    entry: RpgMakerTextEntry,
) -> list[Any] | None:
    origin = entry.origin
    if origin.file_name == "CommonEvents.json":
        if not isinstance(data, list):
            return None
        event = _event_by_id(data, origin.event_id)
        if not isinstance(event, dict):
            return None
        commands = event.get("list")
        return commands if isinstance(commands, list) else None

    if origin.file_name == "Troops.json":
        if not isinstance(data, list) or origin.database_id is None:
            return None
        troop = _database_item_by_id(data, origin.database_id)
        if not isinstance(troop, dict):
            return None
        pages = troop.get("pages")
        if not isinstance(pages, list) or origin.page_index is None:
            return None
        if origin.page_index < 0 or origin.page_index >= len(pages):
            return None
        page = pages[origin.page_index]
        if not isinstance(page, dict):
            return None
        commands = page.get("list")
        return commands if isinstance(commands, list) else None

    if origin.file_name == "Scenario.json":
        if not isinstance(data, dict) or origin.field_name is None:
            return None
        commands = data.get(origin.field_name)
        return commands if isinstance(commands, list) else None

    if not isinstance(data, dict):
        return None
    events = data.get("events")
    event = _event_by_id(_iter_events(events), origin.event_id)
    if not isinstance(event, dict):
        return None
    pages = event.get("pages")
    if not isinstance(pages, list) or origin.page_index is None:
        return None
    if origin.page_index < 0 or origin.page_index >= len(pages):
        return None
    page = pages[origin.page_index]
    if not isinstance(page, dict):
        return None
    commands = page.get("list")
    return commands if isinstance(commands, list) else None


def _replace_grouped_commands(
    commands: list[Any],
    start_index: int,
    *,
    code: int,
    source_text: str,
    translated_text: str,
    line_limit: int,
    reflow_short_lines: bool,
) -> bool | None:
    end_index = start_index
    source_lines: list[str] = []
    while end_index < len(commands):
        command = commands[end_index]
        if not isinstance(command, dict) or command.get("code") != code:
            break
        parameters = command.get("parameters")
        if not isinstance(parameters, list) or not parameters:
            break
        text = parameters[0]
        if not isinstance(text, str):
            break
        source_lines.append(text)
        end_index += 1

    if "\n".join(source_lines) != source_text:
        return None

    template = commands[start_index]
    if not isinstance(template, dict):
        return None
    indent = template.get("indent", 0)
    translated_lines = _message_translation_lines(
        translated_text,
        width=line_limit,
        reflow_short_lines=reflow_short_lines,
    )
    replacement = [
        {"code": code, "indent": indent, "parameters": [line]}
        for line in translated_lines
    ]
    commands[start_index:end_index] = replacement
    return True


def _replace_choice(
    command: dict[str, Any],
    entry: RpgMakerTextEntry,
    translated_text: str,
) -> bool | None:
    code = command.get("code")
    if code == 102:
        parameters = command.get("parameters")
        choice_index = entry.origin.parameter_index
        if (
            not isinstance(parameters, list)
            or not parameters
            or not isinstance(parameters[0], list)
            or choice_index is None
            or choice_index < 0
            or choice_index >= len(parameters[0])
            or parameters[0][choice_index] != entry.source_text
        ):
            return None
        parameters[0][choice_index] = translated_text
        return True

    if code == 402:
        return _replace_parameter(command, 402, 1, entry, translated_text)
    return None


def _replace_speaker(
    command: dict[str, Any],
    entry: RpgMakerTextEntry,
    translated_text: str,
) -> bool | None:
    if command.get("code") == 101:
        return _replace_parameter(command, 101, 4, entry, translated_text)
    if command.get("code") == 356:
        return _replace_tachie_show_name(command, entry, translated_text)
    return None


def _replace_tachie_show_name(
    command: dict[str, Any],
    entry: RpgMakerTextEntry,
    translated_text: str,
) -> bool | None:
    parameters = command.get("parameters")
    parameter_index = entry.origin.parameter_index
    if (
        not isinstance(parameters, list)
        or parameter_index is None
        or parameter_index < 0
        or parameter_index >= len(parameters)
        or not isinstance(parameters[parameter_index], str)
    ):
        return None

    raw_command = parameters[parameter_index]
    match = _TACHIE_SHOW_NAME_PATTERN.match(raw_command)
    if match is None or match.group("name").strip() != entry.source_text:
        return None

    parameters[parameter_index] = (
        f"{match.group('prefix')}{translated_text}{match.group('suffix')}"
    )
    return True


def _replace_parameter(
    command: dict[str, Any],
    code: int,
    parameter_index: int,
    entry: RpgMakerTextEntry,
    translated_text: str,
) -> bool | None:
    parameters = command.get("parameters")
    if (
        command.get("code") != code
        or not isinstance(parameters, list)
        or len(parameters) <= parameter_index
        or parameters[parameter_index] != entry.source_text
    ):
        return None
    parameters[parameter_index] = translated_text
    return True


def _wrapped_translation_lines(
    text: str,
    *,
    width: int,
    normalize_lines: bool,
) -> list[str]:
    if normalize_lines:
        lines = [" ".join(text.split())]
    else:
        lines = text.splitlines()
    if not lines:
        return [text]

    wrapped_lines: list[str] = []
    for line in lines:
        if not line:
            wrapped_lines.append(line)
            continue
        wrapped = textwrap.wrap(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped_lines.extend(wrapped or [line])
    return wrapped_lines


def _message_translation_lines(
    text: str,
    *,
    width: int,
    reflow_short_lines: bool,
) -> list[str]:
    if not reflow_short_lines or not _should_reflow_message_lines(text, width=width):
        return _wrapped_translation_lines(
            text,
            width=width,
            normalize_lines=False,
        )
    return _wrapped_translation_lines(
        text,
        width=width,
        normalize_lines=True,
    )


def _should_reflow_message_lines(text: str, *, width: int) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    if not any(len(line) <= MESSAGE_SHORT_LINE_REFLOW_LIMIT for line in lines[1:-1]):
        return False
    collapsed = _wrapped_translation_lines(text, width=width, normalize_lines=True)
    return len(collapsed) < len(lines)


def _event_by_id(events: Iterable[Any], event_id: int | None) -> Any | None:
    for event in events:
        if not isinstance(event, dict):
            continue
        if event_id is None or event.get("id") == event_id:
            return event
    return None


def _iter_events(events: Any) -> Iterable[Any]:
    if isinstance(events, dict):
        return events.values()
    if isinstance(events, list):
        return events
    return []


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def _skipped_entry(entry: RpgMakerTextEntry, reason: str) -> dict[str, object]:
    origin = entry.origin
    return {
        "entry_id": entry.id,
        "text_type": entry.text_type.value,
        "source_text": entry.source_text,
        "reason": reason,
        "file_name": origin.file_name,
        "origin_key": origin.origin_key,
    }


def _build_markdown_report(report: dict[str, object]) -> str:
    return "\n".join(
        (
            "# RPG Maker MV/MZ Translation Patch",
            "",
            f"- Project: `{report['project_root']}`",
            f"- Patch data: `{report['patch_data_path']}`",
            f"- Applied entries: {report['applied_entries']}",
            f"- Missing cache: {report['missing_cache']}",
            f"- Invalid translations: {report['invalid_translations']}",
            f"- Source mismatches: {report['source_mismatches']}",
            f"- Skipped speakers: {report['skipped_speakers']}",
            f"- Files written: {report['files_written']}",
            "",
        )
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
