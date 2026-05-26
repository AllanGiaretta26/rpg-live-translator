from __future__ import annotations

from pathlib import Path

from scripts.create_profile import build_parser, main


def test_create_profile_command_saves_active_profile(tmp_path, monkeypatch, capsys):
    database_path = tmp_path / "app.sqlite3"
    monkeypatch.setenv("LIVE_TRANSLATOR_DATABASE_PATH", str(database_path))

    exit_code = main(
        [
            "--name",
            "Demo",
            "--window-title",
            "RPG Maker",
            "--x",
            "10",
            "--y",
            "20",
            "--width",
            "300",
            "--height",
            "120",
        ]
    )

    assert exit_code == 0
    assert database_path.exists()
    assert "Active profile saved: Demo" in capsys.readouterr().out


def test_create_profile_parser_requires_region_values():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--name",
            "Demo",
            "--window-title",
            "Game",
            "--x",
            "1",
            "--y",
            "2",
            "--width",
            "3",
            "--height",
            "4",
        ]
    )

    assert args.name == "Demo"
    assert args.x == 1
