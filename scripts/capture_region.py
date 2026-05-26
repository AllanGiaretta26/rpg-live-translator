from __future__ import annotations

import argparse
from pathlib import Path

from config.settings import AppSettings
from domain.models import TextRegion
from infrastructure.capture.mss_screen_capture import MSSScreenCapture
from infrastructure.persistence.game_profile_repository import SQLiteGameProfileRepository
from infrastructure.persistence.settings_repository import SQLiteSettingsRepository
from infrastructure.persistence.sqlite_connection import SQLiteConnectionManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture the active profile region or explicit coordinates."
    )
    parser.add_argument("--x", type=int, help="Capture region left.")
    parser.add_argument("--y", type=int, help="Capture region top.")
    parser.add_argument("--width", type=int, help="Capture region width.")
    parser.add_argument("--height", type=int, help="Capture region height.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("captures") / "latest.png",
        help="PNG output path.",
    )
    return parser


def _region_from_args(args: argparse.Namespace) -> TextRegion | None:
    values = [args.x, args.y, args.width, args.height]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("--x, --y, --width and --height must be provided together")
    return TextRegion(x=args.x, y=args.y, width=args.width, height=args.height)


def _active_profile_region() -> TextRegion:
    settings = AppSettings()
    database = SQLiteConnectionManager(settings.database_path)
    settings_repository = SQLiteSettingsRepository(database)
    profile_repository = SQLiteGameProfileRepository(database, settings_repository)
    profile = profile_repository.get_active_profile()
    if profile is None:
        raise RuntimeError(
            "No active profile found. Run scripts.create_profile first or pass "
            "--x --y --width --height."
        )
    return profile.text_region


def capture_region(args: argparse.Namespace) -> Path:
    region = _region_from_args(args) or _active_profile_region()
    image = MSSScreenCapture().capture_region(region)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    return args.output


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = capture_region(args)
    print(f"Captured region saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
