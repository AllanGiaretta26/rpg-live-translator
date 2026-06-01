from __future__ import annotations

import json

from live_translator.application.rpg_maker_patch_service import RpgMakerPatchService
from live_translator.domain.models import (
    RpgMakerProject,
    RpgMakerTextEntry,
    RpgMakerTextOrigin,
    RpgMakerTextType,
    RpgMakerVersion,
    TranslationResult,
)


class FakeTranslationCache:
    def __init__(self, results: dict[str, str] | None = None) -> None:
        self.results = results or {}

    def get_by_text(self, source_text: str) -> TranslationResult | None:
        translated = self.results.get(source_text)
        if translated is None:
            return None
        return TranslationResult(
            source_text=source_text,
            translated_text=translated,
        )

    def save_translation(self, result: TranslationResult) -> None:
        self.results[result.source_text] = result.translated_text

    def delete_by_text(self, source_text: str) -> bool:
        return self.results.pop(source_text, None) is not None


def test_export_patch_rewrites_messages_choices_and_scrolling_text(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Map001.json",
        {
            "events": [
                None,
                {
                    "id": 7,
                    "pages": [
                        {
                            "list": [
                                {
                                    "code": 101,
                                    "indent": 0,
                                    "parameters": ["", 0, 0, 2, "Alice"],
                                },
                                {"code": 401, "indent": 0, "parameters": ["Hello."]},
                                {
                                    "code": 401,
                                    "indent": 0,
                                    "parameters": ["Second line."],
                                },
                                {
                                    "code": 102,
                                    "indent": 0,
                                    "parameters": [["Yes", "No"]],
                                },
                                {"code": 402, "indent": 0, "parameters": [0, "Yes"]},
                                {
                                    "code": 405,
                                    "indent": 0,
                                    "parameters": ["Long ago..."],
                                },
                            ]
                        }
                    ],
                },
            ]
        },
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Hello.\nSecond line.": "Ola.\nSegunda linha.",
                "Yes": "Sim",
                "No": "Nao",
                "Long ago...": "Ha muito...",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _entry("Hello.\nSecond line.", RpgMakerTextType.MESSAGE, 1),
            _entry("Yes", RpgMakerTextType.CHOICE, 3, parameter_index=0),
            _entry("No", RpgMakerTextType.CHOICE, 3, parameter_index=1),
            _entry("Yes", RpgMakerTextType.CHOICE, 4, parameter_index=1),
            _entry("Long ago...", RpgMakerTextType.SCROLLING_TEXT, 5),
        ],
    )

    patched = _read_json(result.data_path / "Map001.json")
    commands = patched["events"][1]["pages"][0]["list"]
    assert commands[1]["parameters"][0] == "Ola."
    assert commands[2]["parameters"][0] == "Segunda linha."
    assert commands[3]["parameters"][0] == ["Sim", "Nao"]
    assert commands[4]["parameters"][1] == "Sim"
    assert commands[5]["parameters"][0] == "Ha muito..."
    assert result.applied_entries == 5
    assert result.files_written == 1


def test_export_patch_respects_speaker_option(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Map001.json",
        {
            "events": [
                None,
                {
                    "id": 7,
                    "pages": [
                        {
                            "list": [
                                {
                                    "code": 101,
                                    "indent": 0,
                                    "parameters": ["", 0, 0, 2, "Alice"],
                                },
                            ]
                        }
                    ],
                },
            ]
        },
    )
    service = RpgMakerPatchService(
        FakeTranslationCache({"Alice": "Alicia"}),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    skipped = service.export_patch(
        project=project,
        entries=[_entry("Alice", RpgMakerTextType.SPEAKER, 0, parameter_index=4)],
        include_speakers=False,
    )
    included = service.export_patch(
        project=project,
        entries=[_entry("Alice", RpgMakerTextType.SPEAKER, 0, parameter_index=4)],
        include_speakers=True,
    )

    patched = _read_json(included.data_path / "Map001.json")
    assert skipped.skipped_speakers == 1
    assert skipped.files_written == 0
    assert patched["events"][1]["pages"][0]["list"][0]["parameters"][4] == "Alicia"


def test_export_patch_reports_missing_invalid_and_mismatched_entries(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Map001.json",
        {
            "events": [
                None,
                {
                    "id": 7,
                    "pages": [
                        {
                            "list": [
                                {"code": 401, "indent": 0, "parameters": ["Different"]},
                                {"code": 0, "indent": 0, "parameters": []},
                                {"code": 401, "indent": 0, "parameters": ["NoCache"]},
                                {"code": 0, "indent": 0, "parameters": []},
                                {"code": 401, "indent": 0, "parameters": ["Bad"]},
                            ]
                        }
                    ],
                },
            ]
        },
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Hello": "Ola",
                "Bad": "Responda apenas JSON valido.",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _entry("Hello", RpgMakerTextType.MESSAGE, 0),
            _entry("NoCache", RpgMakerTextType.MESSAGE, 2),
            _entry("Bad", RpgMakerTextType.MESSAGE, 4),
        ],
    )

    assert result.source_mismatches == 1
    assert result.missing_cache == 1
    assert result.invalid_translations == 1
    assert result.applied_entries == 0
    assert result.files_written == 0


def test_apply_patch_creates_backup_and_restore_latest_backup_restores_original(
    tmp_path,
):
    project = _project(tmp_path)
    original = {"events": [None, {"id": 7, "pages": [{"list": []}]}]}
    translated = {"events": [None, {"id": 7, "pages": [{"list": [{"code": 0}]}]}]}
    _write_json(project.data_path / "Map001.json", original)
    patch_path = tmp_path / "exports" / "patch"
    (patch_path / "data").mkdir(parents=True)
    _write_json(patch_path / "data" / "Map001.json", translated)
    service = RpgMakerPatchService(
        FakeTranslationCache(),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    applied = service.apply_patch(project=project, patch_path=patch_path)
    restored_after_apply = _read_json(project.data_path / "Map001.json")
    restored = service.restore_latest_backup(project=project)

    assert applied.files_applied == 1
    assert (applied.backup_path / "data" / "Map001.json").exists()
    assert restored_after_apply == translated
    assert restored.backup_path == applied.backup_path
    assert restored.files_restored == 1
    assert _read_json(project.data_path / "Map001.json") == original


def _project(tmp_path) -> RpgMakerProject:
    data_path = tmp_path / "Game" / "www" / "data"
    data_path.mkdir(parents=True)
    return RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=data_path,
        version=RpgMakerVersion.MZ,
    )


def _entry(
    text: str,
    text_type: RpgMakerTextType,
    command_index: int,
    *,
    parameter_index: int = 0,
) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        source_text=text,
        text_type=text_type,
        origin=RpgMakerTextOrigin(
            file_name="Map001.json",
            origin_key=f"Map001.json||7|0|{command_index}|{parameter_index}",
            map_id=1,
            event_id=7,
            page_index=0,
            command_index=command_index,
            parameter_index=parameter_index,
        ),
    )


def _write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))
