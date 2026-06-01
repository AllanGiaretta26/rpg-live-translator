from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

from live_translator.application.translation_quality import (
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
        export_root: Path = Path("exports") / "patches",
        backup_root: Path = Path("backups") / "patches",
    ) -> None:
        self._translation_cache = translation_cache
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

            cached = self._translation_cache.get_by_text(entry.source_text)
            if cached is None:
                counts["missing_cache"] += 1
                skipped.append(_skipped_entry(entry, "missing cache"))
                continue
            if looks_like_invalid_translation(
                entry.source_text,
                cached.translated_text,
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
    }
)


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
    command_list = _command_list_for_entry(data, entry)
    if command_list is None or entry.origin.command_index is None:
        return None
    command_index = entry.origin.command_index
    if command_index < 0 or command_index >= len(command_list):
        return None

    command = command_list[command_index]
    if not isinstance(command, dict):
        return None

    if entry.text_type == RpgMakerTextType.MESSAGE:
        return _replace_grouped_commands(
            command_list,
            command_index,
            code=401,
            source_text=entry.source_text,
            translated_text=plan_entry.translated_text,
        )
    if entry.text_type == RpgMakerTextType.SCROLLING_TEXT:
        return _replace_grouped_commands(
            command_list,
            command_index,
            code=405,
            source_text=entry.source_text,
            translated_text=plan_entry.translated_text,
        )
    if entry.text_type == RpgMakerTextType.CHOICE:
        return _replace_choice(command, entry, plan_entry.translated_text)
    if entry.text_type == RpgMakerTextType.SPEAKER:
        return _replace_parameter(command, 101, 4, entry, plan_entry.translated_text)
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
    replacement = [
        {"code": code, "indent": indent, "parameters": [line]}
        for line in _translation_lines(translated_text)
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


def _translation_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return [text]
    return lines


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
