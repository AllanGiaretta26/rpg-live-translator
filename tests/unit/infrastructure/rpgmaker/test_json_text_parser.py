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
                                    {"code": 401, "parameters": ["Second line."]},
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
        ("Hello.\nSecond line.", RpgMakerTextType.MESSAGE),
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


def test_parser_extracts_items_and_skills_database_text(tmp_path):
    data_path = tmp_path / "Game" / "www" / "data"
    data_path.mkdir(parents=True)
    (data_path / "CommonEvents.json").write_text("[]", encoding="utf-8")
    (data_path / "Items.json").write_text(
        json.dumps(
            [
                None,
                {"id": 1, "name": "Potion", "description": "Restores HP."},
                {"id": 2, "name": "", "description": "   "},
                {"id": "3", "name": "Ether", "description": "Restores MP."},
            ]
        ),
        encoding="utf-8",
    )
    (data_path / "Skills.json").write_text(
        json.dumps(
            [
                None,
                {"id": 1, "name": "Fire", "description": "Deals fire damage."},
                {"name": "No ID", "description": "Ignored."},
            ]
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
        ("Potion", RpgMakerTextType.ITEM_NAME),
        ("Restores HP.", RpgMakerTextType.ITEM_DESCRIPTION),
        ("Ether", RpgMakerTextType.ITEM_NAME),
        ("Restores MP.", RpgMakerTextType.ITEM_DESCRIPTION),
        ("Fire", RpgMakerTextType.SKILL_NAME),
        ("Deals fire damage.", RpgMakerTextType.SKILL_DESCRIPTION),
    ]
    assert entries[0].origin.file_name == "Items.json"
    assert entries[0].origin.database_id == 1
    assert entries[0].origin.field_name == "name"
    assert entries[5].origin.file_name == "Skills.json"
    assert entries[5].origin.database_id == 1
    assert entries[5].origin.field_name == "description"


def test_parser_extracts_extended_database_text_and_troop_events(tmp_path):
    data_path = tmp_path / "Game" / "www" / "data"
    data_path.mkdir(parents=True)
    (data_path / "Weapons.json").write_text(
        json.dumps([None, {"id": 1, "name": "Sword", "description": "A sharp blade."}]),
        encoding="utf-8",
    )
    (data_path / "Armors.json").write_text(
        json.dumps([None, {"id": 2, "name": "Shield", "description": "Blocks hits."}]),
        encoding="utf-8",
    )
    (data_path / "States.json").write_text(
        json.dumps(
            [
                None,
                {
                    "id": 3,
                    "name": "Poison",
                    "message1": "%1 is poisoned!",
                    "message2": "%1 is still poisoned!",
                    "message3": "",
                    "message4": None,
                },
            ]
        ),
        encoding="utf-8",
    )
    (data_path / "Classes.json").write_text(
        json.dumps([None, {"id": 4, "name": "Warrior"}]),
        encoding="utf-8",
    )
    (data_path / "Enemies.json").write_text(
        json.dumps([None, {"id": 5, "name": "Slime"}]),
        encoding="utf-8",
    )
    (data_path / "Skills.json").write_text(
        json.dumps(
            [
                None,
                {
                    "id": 6,
                    "name": "Fire",
                    "description": "Deals fire damage.",
                    "message1": "%1 casts %2!",
                    "message2": "%1 uses %2!",
                },
            ]
        ),
        encoding="utf-8",
    )
    (data_path / "Troops.json").write_text(
        json.dumps(
            [
                None,
                {
                    "id": 7,
                    "pages": [
                        {
                            "list": [
                                {"code": 101, "parameters": ["", 0, 0, 2, "Boss"]},
                                {"code": 401, "parameters": ["Attack!"]},
                                {"code": 102, "parameters": [["Fight"]]},
                                {"code": 405, "parameters": ["The ground shakes."]},
                            ]
                        }
                    ],
                },
            ]
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
        ("Fire", RpgMakerTextType.SKILL_NAME),
        ("Deals fire damage.", RpgMakerTextType.SKILL_DESCRIPTION),
        ("%1 casts %2!", RpgMakerTextType.SKILL_MESSAGE),
        ("%1 uses %2!", RpgMakerTextType.SKILL_MESSAGE),
        ("Sword", RpgMakerTextType.WEAPON_NAME),
        ("A sharp blade.", RpgMakerTextType.WEAPON_DESCRIPTION),
        ("Shield", RpgMakerTextType.ARMOR_NAME),
        ("Blocks hits.", RpgMakerTextType.ARMOR_DESCRIPTION),
        ("Poison", RpgMakerTextType.STATE_NAME),
        ("%1 is poisoned!", RpgMakerTextType.STATE_MESSAGE),
        ("%1 is still poisoned!", RpgMakerTextType.STATE_MESSAGE),
        ("Warrior", RpgMakerTextType.CLASS_NAME),
        ("Slime", RpgMakerTextType.ENEMY_NAME),
        ("Boss", RpgMakerTextType.TROOP_SPEAKER),
        ("Attack!", RpgMakerTextType.TROOP_MESSAGE),
        ("Fight", RpgMakerTextType.TROOP_CHOICE),
        ("The ground shakes.", RpgMakerTextType.TROOP_SCROLLING_TEXT),
    ]
    assert entries[13].origin.file_name == "Troops.json"
    assert entries[13].origin.database_id == 7
    assert entries[13].origin.page_index == 0
    assert entries[13].origin.command_index == 0
    assert entries[13].origin.parameter_index == 4


def test_parser_extracts_actor_names_and_system_terms(tmp_path):
    data_path = tmp_path / "Game" / "www" / "data"
    data_path.mkdir(parents=True)
    (data_path / "CommonEvents.json").write_text("[]", encoding="utf-8")
    (data_path / "Actors.json").write_text(
        json.dumps(
            [
                None,
                {"id": 1, "name": "Hero", "nickname": "Ignored"},
            ]
        ),
        encoding="utf-8",
    )
    (data_path / "System.json").write_text(
        json.dumps(
            {
                "terms": {
                    "commands": ["Fight", "Escape", "Item", "Skill"],
                    "basic": {"level": "Level"},
                }
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
        ("Hero", RpgMakerTextType.ACTOR_NAME),
        ("Fight", RpgMakerTextType.SYSTEM_TERM),
        ("Escape", RpgMakerTextType.SYSTEM_TERM),
        ("Item", RpgMakerTextType.SYSTEM_TERM),
        ("Skill", RpgMakerTextType.SYSTEM_TERM),
        ("Level", RpgMakerTextType.SYSTEM_TERM),
    ]
    assert entries[0].origin.file_name == "Actors.json"
    assert entries[0].origin.database_id == 1
    assert entries[0].origin.field_name == "name"
    assert entries[3].origin.file_name == "System.json"
    assert entries[3].origin.field_name == "terms.commands.2"
