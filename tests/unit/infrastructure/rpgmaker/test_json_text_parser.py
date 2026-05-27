from __future__ import annotations

import json

from live_translator.domain.models import (
    RpgMakerProject,
    RpgMakerTextType,
    RpgMakerVersion,
)
from live_translator.infrastructure.rpgmaker.json_text_parser import (
    RpgMakerJsonTextParser,
)


def test_parser_extracts_map_messages_choices_and_scrolling_text(tmp_path):
    data_path = tmp_path / "Game" / "www" / "data"
    data_path.mkdir(parents=True)
    (data_path / "CommonEvents.json").write_text("[]", encoding="utf-8")
    (data_path / "Map001.json").write_text(
        json.dumps(
            {
                "events": [
                    None,
                    {
                        "id": 7,
                        "pages": [
                            {
                                "list": [
                                    {"code": 101, "parameters": ["", 0, 0, 2, "Alice"]},
                                    {"code": 401, "parameters": ["Hello."]},
                                    {"code": 102, "parameters": [["Yes", "No"]]},
                                    {"code": 402, "parameters": [0, "Yes"]},
                                    {"code": 405, "parameters": ["Long ago..."]},
                                ]
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=data_path,
        version=RpgMakerVersion.MZ,
    )

    entries = RpgMakerJsonTextParser().parse_project(project)

    assert [(entry.source_text, entry.text_type) for entry in entries] == [
        ("Alice", RpgMakerTextType.SPEAKER),
        ("Hello.", RpgMakerTextType.MESSAGE),
        ("Yes", RpgMakerTextType.CHOICE),
        ("No", RpgMakerTextType.CHOICE),
        ("Yes", RpgMakerTextType.CHOICE),
        ("Long ago...", RpgMakerTextType.SCROLLING_TEXT),
    ]
    assert entries[1].origin.file_name == "Map001.json"
    assert entries[1].origin.map_id == 1
    assert entries[1].origin.event_id == 7
    assert entries[1].origin.page_index == 0
    assert entries[1].origin.command_index == 1


def test_parser_extracts_common_event_messages(tmp_path):
    data_path = tmp_path / "Game" / "data"
    data_path.mkdir(parents=True)
    (data_path / "CommonEvents.json").write_text(
        json.dumps(
            [
                None,
                {
                    "id": 3,
                    "list": [
                        {"code": 401, "parameters": ["Common line"]},
                    ],
                },
            ]
        ),
        encoding="utf-8",
    )
    project = RpgMakerProject(
        root_path=tmp_path / "Game",
        data_path=data_path,
        version=RpgMakerVersion.MV,
    )

    entries = RpgMakerJsonTextParser().parse_project(project)

    assert len(entries) == 1
    assert entries[0].source_text == "Common line"
    assert entries[0].origin.file_name == "CommonEvents.json"
    assert entries[0].origin.event_id == 3
