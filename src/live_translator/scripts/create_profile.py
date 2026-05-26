from __future__ import annotations

import argparse

from live_translator.config.settings import AppSettings
from live_translator.domain.models import GameProfile, TextRegion
from live_translator.infrastructure.persistence.game_profile_repository import SQLiteGameProfileRepository
from live_translator.infrastructure.persistence.settings_repository import SQLiteSettingsRepository
from live_translator.infrastructure.persistence.sqlite_connection import SQLiteConnectionManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or update the active game profile."
    )
    parser.add_argument("--name", required=True, help="Profile name.")
    parser.add_argument(
        "--window-title",
        required=True,
        help="Game window title or a recognizable part of it.",
    )
    parser.add_argument("--x", required=True, type=int, help="Capture region left.")
    parser.add_argument("--y", required=True, type=int, help="Capture region top.")
    parser.add_argument("--width", required=True, type=int, help="Capture region width.")
    parser.add_argument("--height", required=True, type=int, help="Capture region height.")
    return parser


def create_profile(args: argparse.Namespace) -> GameProfile:
    settings = AppSettings()
    database = SQLiteConnectionManager(settings.database_path)
    settings_repository = SQLiteSettingsRepository(database)
    profile_repository = SQLiteGameProfileRepository(database, settings_repository)

    profile = GameProfile(
        name=args.name,
        window_title=args.window_title,
        text_region=TextRegion(
            x=args.x,
            y=args.y,
            width=args.width,
            height=args.height,
        ),
    )
    profile_repository.save(profile)
    return profile


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile = create_profile(args)
    print(
        "Active profile saved: "
        f"{profile.name} ({profile.window_title}) "
        f"x={profile.text_region.x} y={profile.text_region.y} "
        f"width={profile.text_region.width} height={profile.text_region.height}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
