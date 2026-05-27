from __future__ import annotations

import json

import pytest

from live_translator.domain.models import RpgMakerVersion
from live_translator.infrastructure.rpgmaker.project_detector import (
    FileSystemRpgMakerProjectDetector,
    RpgMakerProjectDetectionError,
)


def _write_required_data_files(data_path):
    data_path.mkdir(parents=True)
    for name in ("System.json", "MapInfos.json", "CommonEvents.json"):
        (data_path / name).write_text(json.dumps([]), encoding="utf-8")


def test_detects_mz_project_with_www_data(tmp_path):
    data_path = tmp_path / "Game" / "www" / "data"
    _write_required_data_files(data_path)
    js_path = tmp_path / "Game" / "www" / "js"
    js_path.mkdir()
    (js_path / "rmmz_core.js").write_text("", encoding="utf-8")

    project = FileSystemRpgMakerProjectDetector().detect(tmp_path / "Game")

    assert project.root_path == tmp_path / "Game"
    assert project.data_path == data_path
    assert project.version == RpgMakerVersion.MZ


def test_detects_mv_project_with_data_folder(tmp_path):
    data_path = tmp_path / "Game" / "data"
    _write_required_data_files(data_path)
    js_path = tmp_path / "Game" / "js"
    js_path.mkdir()
    (js_path / "rpg_core.js").write_text("", encoding="utf-8")

    project = FileSystemRpgMakerProjectDetector().detect(data_path)

    assert project.root_path == tmp_path / "Game"
    assert project.data_path == data_path
    assert project.version == RpgMakerVersion.MV


def test_rejects_folder_without_required_jsons(tmp_path):
    data_path = tmp_path / "Game" / "www" / "data"
    data_path.mkdir(parents=True)

    with pytest.raises(RpgMakerProjectDetectionError):
        FileSystemRpgMakerProjectDetector().detect(tmp_path / "Game")
