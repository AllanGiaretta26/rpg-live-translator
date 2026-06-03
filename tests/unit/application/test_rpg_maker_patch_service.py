from __future__ import annotations

import json

from live_translator.application.rpg_maker_patch_service import (
    MESSAGE_LINE_LIMIT,
    RpgMakerPatchService,
)
from live_translator.application.translation_quality import (
    RPG_MAKER_DESCRIPTION_LINE_LIMIT,
    RPG_MAKER_DESCRIPTION_MAX_LINES,
)
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
        self.lookup_scopes: list[str | None] = []

    def get_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> TranslationResult | None:
        self.lookup_scopes.append(scope)
        translated = self.results.get(source_text)
        if translated is None:
            return None
        return TranslationResult(
            source_text=source_text,
            translated_text=translated,
        )

    def save_translation(
        self,
        result: TranslationResult,
        *,
        scope: str | None = None,
    ) -> None:
        self.results[result.source_text] = result.translated_text

    def delete_by_text(
        self,
        source_text: str,
        *,
        scope: str | None = None,
    ) -> bool:
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


def test_export_patch_rewrites_scenario_command_lists(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Scenario.json",
        {
            "intro": [
                {
                    "code": 356,
                    "indent": 0,
                    "parameters": ["Tachie showName Deathpolca"],
                },
                {"code": 401, "indent": 0, "parameters": ["Alright."]},
                {"code": 401, "indent": 0, "parameters": ["Second line."]},
                {"code": 102, "indent": 0, "parameters": [["Fight", "Wait"]]},
                {"code": 402, "indent": 0, "parameters": [0, "Fight"]},
                {"code": 405, "indent": 0, "parameters": ["Long ago..."]},
            ],
            "other": [
                {"code": 401, "indent": 0, "parameters": ["Do not touch."]},
            ],
        },
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Deathpolca": "Deathpolca PT",
                "Alright.\nSecond line.": "Tudo certo.\nSegunda linha.",
                "Fight": "Lutar",
                "Wait": "Esperar",
                "Long ago...": "Ha muito...",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _scenario_entry("Deathpolca", RpgMakerTextType.SPEAKER, "intro", 0, 0),
            _scenario_entry(
                "Alright.\nSecond line.",
                RpgMakerTextType.MESSAGE,
                "intro",
                1,
                0,
            ),
            _scenario_entry("Fight", RpgMakerTextType.CHOICE, "intro", 3, 0),
            _scenario_entry("Wait", RpgMakerTextType.CHOICE, "intro", 3, 1),
            _scenario_entry("Fight", RpgMakerTextType.CHOICE, "intro", 4, 1),
            _scenario_entry(
                "Long ago...",
                RpgMakerTextType.SCROLLING_TEXT,
                "intro",
                5,
                0,
            ),
        ],
        include_speakers=True,
    )

    patched = _read_json(result.data_path / "Scenario.json")
    intro = patched["intro"]
    assert intro[0]["parameters"][0] == "Tachie showName Deathpolca PT"
    assert intro[1]["parameters"][0] == "Tudo certo."
    assert intro[2]["parameters"][0] == "Segunda linha."
    assert intro[3]["parameters"][0] == ["Lutar", "Esperar"]
    assert intro[4]["parameters"][1] == "Lutar"
    assert intro[5]["parameters"][0] == "Ha muito..."
    assert patched["other"][0]["parameters"][0] == "Do not touch."
    assert result.applied_entries == 6
    assert result.files_written == 1


def test_export_patch_respects_scenario_tachie_speaker_option(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Scenario.json",
        {
            "intro": [
                {
                    "code": 356,
                    "indent": 0,
                    "parameters": ["Tachie showName Deathpolca"],
                },
            ],
        },
    )
    service = RpgMakerPatchService(
        FakeTranslationCache({"Deathpolca": "Deathpolca PT"}),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    skipped = service.export_patch(
        project=project,
        entries=[
            _scenario_entry("Deathpolca", RpgMakerTextType.SPEAKER, "intro", 0, 0)
        ],
        include_speakers=False,
    )
    included = service.export_patch(
        project=project,
        entries=[
            _scenario_entry("Deathpolca", RpgMakerTextType.SPEAKER, "intro", 0, 0)
        ],
        include_speakers=True,
    )

    patched = _read_json(included.data_path / "Scenario.json")
    assert skipped.skipped_speakers == 1
    assert skipped.files_written == 0
    assert patched["intro"][0]["parameters"][0] == "Tachie showName Deathpolca PT"


def test_export_patch_reports_missing_scenario_cache(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Scenario.json",
        {
            "intro": [
                {"code": 401, "indent": 0, "parameters": ["Uncached."]},
            ],
        },
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[_scenario_entry("Uncached.", RpgMakerTextType.MESSAGE, "intro", 0, 0)],
    )

    report = _read_json(result.report_path)
    assert result.missing_cache == 1
    assert result.files_written == 0
    assert report["skipped"][0]["file_name"] == "Scenario.json"
    assert report["skipped"][0]["origin_key"] == "Scenario.json|scenario|intro|0|0"


def test_export_patch_rewrites_troop_event_commands(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Troops.json",
        [
            None,
            {
                "id": 4,
                "pages": [
                    {
                        "list": [
                            {
                                "code": 101,
                                "indent": 0,
                                "parameters": ["", 0, 0, 2, "Commander"],
                            },
                            {"code": 401, "indent": 0, "parameters": ["Attack!"]},
                            {"code": 102, "indent": 0, "parameters": [["Fight"]]},
                            {
                                "code": 405,
                                "indent": 0,
                                "parameters": ["The ground shakes."],
                            },
                        ]
                    }
                ],
            },
        ],
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Commander": "Comandante",
                "Attack!": "Ataquem!",
                "Fight": "Lutar",
                "The ground shakes.": "O chao treme.",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _troop_entry("Commander", RpgMakerTextType.TROOP_SPEAKER, 0, 4),
            _troop_entry("Attack!", RpgMakerTextType.TROOP_MESSAGE, 1, 0),
            _troop_entry("Fight", RpgMakerTextType.TROOP_CHOICE, 2, 0),
            _troop_entry(
                "The ground shakes.",
                RpgMakerTextType.TROOP_SCROLLING_TEXT,
                3,
                0,
            ),
        ],
    )

    patched = _read_json(result.data_path / "Troops.json")
    commands = patched[1]["pages"][0]["list"]
    assert commands[0]["parameters"][4] == "Comandante"
    assert commands[1]["parameters"][0] == "Ataquem!"
    assert commands[2]["parameters"][0] == ["Lutar"]
    assert commands[3]["parameters"][0] == "O chao treme."
    assert result.applied_entries == 4
    assert result.files_written == 1


def test_export_patch_rewrites_items_and_skills_database(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Items.json",
        [
            None,
            {"id": 1, "name": "Potion", "description": "Restores HP."},
        ],
    )
    _write_json(
        project.data_path / "Skills.json",
        [
            None,
            {"id": 1, "name": "Fire", "description": "Deals fire damage."},
        ],
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Potion": "Pocao",
                "Restores HP.": "Restaura HP.",
                "Fire": "Fogo",
                "Deals fire damage.": "Causa dano de fogo.",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _database_entry(
                "Potion",
                RpgMakerTextType.ITEM_NAME,
                "Items.json",
                1,
                "name",
            ),
            _database_entry(
                "Restores HP.",
                RpgMakerTextType.ITEM_DESCRIPTION,
                "Items.json",
                1,
                "description",
            ),
            _database_entry(
                "Fire",
                RpgMakerTextType.SKILL_NAME,
                "Skills.json",
                1,
                "name",
            ),
            _database_entry(
                "Deals fire damage.",
                RpgMakerTextType.SKILL_DESCRIPTION,
                "Skills.json",
                1,
                "description",
            ),
        ],
    )

    patched_items = _read_json(result.data_path / "Items.json")
    patched_skills = _read_json(result.data_path / "Skills.json")
    assert patched_items[1]["name"] == "Pocao"
    assert patched_items[1]["description"] == "Restaura HP."
    assert patched_skills[1]["name"] == "Fogo"
    assert patched_skills[1]["description"] == "Causa dano de fogo."
    assert result.applied_entries == 4
    assert result.files_written == 2


def test_export_patch_wraps_database_descriptions_for_help_windows(tmp_path):
    project = _project(tmp_path)
    cases = [
        (
            "Items.json",
            RpgMakerTextType.ITEM_DESCRIPTION,
            "Restores HP and MP to one ally over time.",
            "Restaura HP e MP de um aliado ao longo do tempo durante a batalha.",
        ),
        (
            "Skills.json",
            RpgMakerTextType.SKILL_DESCRIPTION,
            "Hits all enemies with a fast piercing strike.",
            "Atinge todos os inimigos com um golpe rapido e perfurante.",
        ),
        (
            "Weapons.json",
            RpgMakerTextType.WEAPON_DESCRIPTION,
            "A blade with a sharp reinforced edge.",
            "Lamina reforcada com fio afiado para ataques muito precisos.",
        ),
        (
            "Armors.json",
            RpgMakerTextType.ARMOR_DESCRIPTION,
            "Light armor that reduces incoming damage.",
            "Armadura leve que reduz o dano recebido em combate prolongado.",
        ),
    ]
    for file_name, _text_type, source_text, _translated_text in cases:
        _write_json(
            project.data_path / file_name,
            [None, {"id": 1, "name": "Entry", "description": source_text}],
        )

    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                source_text: translated_text
                for _, _, source_text, translated_text in cases
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _database_entry(source_text, text_type, file_name, 1, "description")
            for file_name, text_type, source_text, _translated_text in cases
        ],
    )

    assert result.applied_entries == 4
    assert result.files_written == 4
    for file_name, _text_type, _source_text, translated_text in cases:
        patched = _read_json(result.data_path / file_name)
        description = patched[1]["description"]
        lines = description.splitlines()
        assert " ".join(description.split()) == translated_text
        assert 1 < len(lines) <= RPG_MAKER_DESCRIPTION_MAX_LINES
        assert all(len(line) <= RPG_MAKER_DESCRIPTION_LINE_LIMIT for line in lines)


def test_export_patch_skips_description_that_cannot_fit_help_window(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Skills.json",
        [
            None,
            {
                "id": 1,
                "name": "Flash",
                "description": "Hits all enemies with a fast piercing strike.",
            },
        ],
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Hits all enemies with a fast piercing strike.": (
                    "Uma habilidade que atravessa todos os inimigos em um flash e "
                    "inflige dano magico continuo por varios turnos enquanto tambem "
                    "reduz a defesa e a resistencia elemental de cada alvo atingido."
                )
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _database_entry(
                "Hits all enemies with a fast piercing strike.",
                RpgMakerTextType.SKILL_DESCRIPTION,
                "Skills.json",
                1,
                "description",
            )
        ],
    )

    assert result.invalid_translations == 1
    assert result.applied_entries == 0
    assert result.files_written == 0
    assert not (result.data_path / "Skills.json").exists()


def test_export_patch_rewrites_extended_database_files(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Weapons.json",
        [None, {"id": 1, "name": "Sword", "description": "A sharp blade."}],
    )
    _write_json(
        project.data_path / "Armors.json",
        [None, {"id": 1, "name": "Shield", "description": "Blocks hits."}],
    )
    _write_json(
        project.data_path / "States.json",
        [
            None,
            {
                "id": 1,
                "name": "Poison",
                "message1": "%1 is poisoned!",
                "message2": "%1 is still poisoned!",
            },
        ],
    )
    _write_json(
        project.data_path / "Classes.json", [None, {"id": 1, "name": "Warrior"}]
    )
    _write_json(project.data_path / "Enemies.json", [None, {"id": 1, "name": "Slime"}])
    _write_json(
        project.data_path / "Skills.json",
        [
            None,
            {
                "id": 1,
                "name": "Fire",
                "description": "Deals fire damage.",
                "message1": "%1 casts %2!",
                "message2": "%1 uses %2!",
            },
        ],
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Sword": "Espada",
                "A sharp blade.": "Lamina afiada.",
                "Shield": "Escudo",
                "Blocks hits.": "Bloqueia golpes.",
                "Poison": "Veneno",
                "%1 is poisoned!": "%1 foi envenenado!",
                "%1 is still poisoned!": "%1 continua envenenado!",
                "Warrior": "Guerreiro",
                "Slime": "Gosma",
                "%1 casts %2!": "%1 conjura %2!",
                "%1 uses %2!": "%1 usa %2!",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _database_entry(
                "Sword", RpgMakerTextType.WEAPON_NAME, "Weapons.json", 1, "name"
            ),
            _database_entry(
                "A sharp blade.",
                RpgMakerTextType.WEAPON_DESCRIPTION,
                "Weapons.json",
                1,
                "description",
            ),
            _database_entry(
                "Shield", RpgMakerTextType.ARMOR_NAME, "Armors.json", 1, "name"
            ),
            _database_entry(
                "Blocks hits.",
                RpgMakerTextType.ARMOR_DESCRIPTION,
                "Armors.json",
                1,
                "description",
            ),
            _database_entry(
                "Poison", RpgMakerTextType.STATE_NAME, "States.json", 1, "name"
            ),
            _database_entry(
                "%1 is poisoned!",
                RpgMakerTextType.STATE_MESSAGE,
                "States.json",
                1,
                "message1",
            ),
            _database_entry(
                "%1 is still poisoned!",
                RpgMakerTextType.STATE_MESSAGE,
                "States.json",
                1,
                "message2",
            ),
            _database_entry(
                "Warrior", RpgMakerTextType.CLASS_NAME, "Classes.json", 1, "name"
            ),
            _database_entry(
                "Slime", RpgMakerTextType.ENEMY_NAME, "Enemies.json", 1, "name"
            ),
            _database_entry(
                "%1 casts %2!",
                RpgMakerTextType.SKILL_MESSAGE,
                "Skills.json",
                1,
                "message1",
            ),
            _database_entry(
                "%1 uses %2!",
                RpgMakerTextType.SKILL_MESSAGE,
                "Skills.json",
                1,
                "message2",
            ),
        ],
    )

    assert _read_json(result.data_path / "Weapons.json")[1]["name"] == "Espada"
    assert _read_json(result.data_path / "Armors.json")[1]["description"] == (
        "Bloqueia golpes."
    )
    assert _read_json(result.data_path / "States.json")[1]["message1"] == (
        "%1 foi envenenado!"
    )
    assert _read_json(result.data_path / "Classes.json")[1]["name"] == "Guerreiro"
    assert _read_json(result.data_path / "Enemies.json")[1]["name"] == "Gosma"
    assert _read_json(result.data_path / "Skills.json")[1]["message2"] == "%1 usa %2!"
    assert result.applied_entries == 11
    assert result.files_written == 6


def test_export_patch_rewrites_actor_names_and_system_terms(tmp_path):
    project = _project(tmp_path)
    _write_json(
        project.data_path / "Actors.json",
        [
            None,
            {"id": 1, "name": "Hero"},
        ],
    )
    _write_json(
        project.data_path / "System.json",
        {"terms": {"commands": ["Fight", "Escape", "Item", "Skill"]}},
    )
    service = RpgMakerPatchService(
        FakeTranslationCache(
            {
                "Hero": "Heroi",
                "Item": "Itens",
                "Skill": "Habilidades",
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[
            _database_entry(
                "Hero",
                RpgMakerTextType.ACTOR_NAME,
                "Actors.json",
                1,
                "name",
            ),
            _system_entry("Item", "terms.commands.2"),
            _system_entry("Skill", "terms.commands.3"),
        ],
    )

    patched_actors = _read_json(result.data_path / "Actors.json")
    patched_system = _read_json(result.data_path / "System.json")
    assert patched_actors[1]["name"] == "Heroi"
    assert patched_system["terms"]["commands"][2] == "Itens"
    assert patched_system["terms"]["commands"][3] == "Habilidades"
    assert result.applied_entries == 3
    assert result.files_written == 2


def test_export_patch_wraps_long_message_lines(tmp_path):
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
                                {"code": 401, "indent": 0, "parameters": ["Hello"]},
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
                "Hello": (
                    "Esta traducao ficou longa demais para caber na caixa de texto "
                    "do jogo sem quebra."
                )
            }
        ),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[_entry("Hello", RpgMakerTextType.MESSAGE, 0)],
    )

    patched = _read_json(result.data_path / "Map001.json")
    commands = patched["events"][1]["pages"][0]["list"]
    lines = [command["parameters"][0] for command in commands]
    assert len(lines) > 1
    assert all(len(line) <= MESSAGE_LINE_LIMIT for line in lines)


def test_export_patch_reflows_cached_message_line_breaks(tmp_path):
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
                                {"code": 401, "indent": 0, "parameters": ["Hello"]},
                            ]
                        }
                    ],
                },
            ]
        },
    )
    translated = (
        "Nos nao temos um pais mais! Nao ha para onde\n"
        "eles irem e\n"
        "nenhum medico para trata-los!"
    )
    service = RpgMakerPatchService(
        FakeTranslationCache({"Hello": translated}),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[_entry("Hello", RpgMakerTextType.MESSAGE, 0)],
    )

    patched = _read_json(result.data_path / "Map001.json")
    commands = patched["events"][1]["pages"][0]["list"]
    lines = [command["parameters"][0] for command in commands]
    assert len(lines) == 2
    assert "eles irem e" not in lines
    assert all(len(line) <= MESSAGE_LINE_LIMIT for line in lines)


def test_export_patch_breaks_message_before_rpg_maker_forced_wrap(tmp_path):
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
                                {"code": 401, "indent": 0, "parameters": ["Hello"]},
                            ]
                        }
                    ],
                },
            ]
        },
    )
    translated = (
        "Antes de invadirmos Bohelos, enviamos alguns embaixadores para o Imperio. "
        "Um foi decapitado na hora, enquanto o outro foi devolvido"
    )
    service = RpgMakerPatchService(
        FakeTranslationCache({"Hello": translated}),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[_entry("Hello", RpgMakerTextType.MESSAGE, 0)],
    )

    patched = _read_json(result.data_path / "Map001.json")
    commands = patched["events"][1]["pages"][0]["list"]
    lines = [command["parameters"][0] for command in commands]
    assert lines == [
        "Antes de invadirmos Bohelos, enviamos alguns embaixadores",
        "para o Imperio. Um foi decapitado na hora, enquanto",
        "o outro foi devolvido",
    ]
    assert all(len(line) <= MESSAGE_LINE_LIMIT for line in lines)


def test_export_patch_keeps_sentence_start_with_next_message_line(tmp_path):
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
                                {"code": 401, "indent": 0, "parameters": ["Hello"]},
                            ]
                        }
                    ],
                },
            ]
        },
    )
    translated = (
        "A garota e responsavel por cuidar dos assuntos humanos. Se e isso que ela "
        "quer fazer, entao eu nao tenho objecoes."
    )
    service = RpgMakerPatchService(
        FakeTranslationCache({"Hello": translated}),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[_entry("Hello", RpgMakerTextType.MESSAGE, 0)],
    )

    patched = _read_json(result.data_path / "Map001.json")
    commands = patched["events"][1]["pages"][0]["list"]
    lines = [command["parameters"][0] for command in commands]
    assert lines == [
        "A garota e responsavel por cuidar dos assuntos humanos.",
        "Se e isso que ela quer fazer, entao eu nao tenho objecoes.",
    ]
    assert all(len(line) <= MESSAGE_LINE_LIMIT for line in lines)


def test_export_patch_breaks_npc_message_at_sentence_boundary(tmp_path):
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
                                {"code": 401, "indent": 0, "parameters": ["Hello"]},
                            ]
                        }
                    ],
                },
            ]
        },
    )
    translated = (
        "Cavaleiro Escravo:\n"
        "Por favor! Por favor, le-! ...Ha? Voce derrotou o Rei de Shingana?"
    )
    service = RpgMakerPatchService(
        FakeTranslationCache({"Hello": translated}),
        export_root=tmp_path / "exports",
        backup_root=tmp_path / "backups",
    )

    result = service.export_patch(
        project=project,
        entries=[_entry("Hello", RpgMakerTextType.MESSAGE, 0)],
    )

    patched = _read_json(result.data_path / "Map001.json")
    commands = patched["events"][1]["pages"][0]["list"]
    lines = [command["parameters"][0] for command in commands]
    assert lines == [
        "Cavaleiro Escravo:",
        "Por favor! Por favor, le-! ...Ha?",
        "Voce derrotou o Rei de Shingana?",
    ]
    assert all(len(line) <= MESSAGE_LINE_LIMIT for line in lines)


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


def _database_entry(
    text: str,
    text_type: RpgMakerTextType,
    file_name: str,
    database_id: int,
    field_name: str,
) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        source_text=text,
        text_type=text_type,
        origin=RpgMakerTextOrigin(
            file_name=file_name,
            origin_key=f"{file_name}|database|{database_id}|{field_name}",
            database_id=database_id,
            field_name=field_name,
        ),
    )


def _troop_entry(
    text: str,
    text_type: RpgMakerTextType,
    command_index: int,
    parameter_index: int,
) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        source_text=text,
        text_type=text_type,
        origin=RpgMakerTextOrigin(
            file_name="Troops.json",
            origin_key=f"Troops.json|database|4|0|{command_index}|{parameter_index}",
            database_id=4,
            page_index=0,
            command_index=command_index,
            parameter_index=parameter_index,
        ),
    )


def _scenario_entry(
    text: str,
    text_type: RpgMakerTextType,
    scenario_key: str,
    command_index: int,
    parameter_index: int,
) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        source_text=text,
        text_type=text_type,
        origin=RpgMakerTextOrigin(
            file_name="Scenario.json",
            origin_key=(
                f"Scenario.json|scenario|{scenario_key}|"
                f"{command_index}|{parameter_index}"
            ),
            field_name=scenario_key,
            command_index=command_index,
            parameter_index=parameter_index,
        ),
    )


def _system_entry(text: str, field_name: str) -> RpgMakerTextEntry:
    return RpgMakerTextEntry(
        source_text=text,
        text_type=RpgMakerTextType.SYSTEM_TERM,
        origin=RpgMakerTextOrigin(
            file_name="System.json",
            origin_key=f"System.json|system|{field_name}",
            field_name=field_name,
        ),
    )


def _write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))
