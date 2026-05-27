from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import defaults

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover
    BaseSettings = None  # type: ignore[assignment]


if BaseSettings is not None:

    class AppSettings(BaseSettings):
        ollama_base_url: str = Field(default=defaults.DEFAULT_OLLAMA_BASE_URL)
        ollama_model: str = Field(default=defaults.DEFAULT_OLLAMA_MODEL)
        ollama_timeout_seconds: float = Field(
            default=defaults.DEFAULT_OLLAMA_TIMEOUT_SECONDS,
            gt=0,
        )

        capture_interval_ms: int = Field(
            default=defaults.DEFAULT_CAPTURE_INTERVAL_MS, gt=0
        )
        source_language: str = Field(default=defaults.DEFAULT_SOURCE_LANGUAGE)
        target_language: str = Field(default=defaults.DEFAULT_TARGET_LANGUAGE)

        overlay_opacity: float = Field(
            default=defaults.DEFAULT_OVERLAY_OPACITY, gt=0, le=1
        )
        overlay_font_size: int = Field(default=defaults.DEFAULT_OVERLAY_FONT_SIZE, gt=0)

        database_path: Path = Field(default=defaults.DEFAULT_DATABASE_PATH)
        capture_preview_path: Path = Field(
            default=defaults.DEFAULT_CAPTURE_PREVIEW_PATH
        )
        rpg_maker_bridge_enabled: bool = Field(
            default=defaults.DEFAULT_RPG_MAKER_BRIDGE_ENABLED
        )
        rpg_maker_bridge_host: str = Field(
            default=defaults.DEFAULT_RPG_MAKER_BRIDGE_HOST
        )
        rpg_maker_bridge_port: int = Field(
            default=defaults.DEFAULT_RPG_MAKER_BRIDGE_PORT,
            gt=0,
            le=65535,
        )

        model_config = SettingsConfigDict(
            env_prefix="LIVE_TRANSLATOR_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )
else:

    @dataclass(slots=True)
    class AppSettings:
        ollama_base_url: str = defaults.DEFAULT_OLLAMA_BASE_URL
        ollama_model: str = defaults.DEFAULT_OLLAMA_MODEL
        ollama_timeout_seconds: float = defaults.DEFAULT_OLLAMA_TIMEOUT_SECONDS
        capture_interval_ms: int = defaults.DEFAULT_CAPTURE_INTERVAL_MS
        source_language: str = defaults.DEFAULT_SOURCE_LANGUAGE
        target_language: str = defaults.DEFAULT_TARGET_LANGUAGE
        overlay_opacity: float = defaults.DEFAULT_OVERLAY_OPACITY
        overlay_font_size: int = defaults.DEFAULT_OVERLAY_FONT_SIZE
        database_path: Path = defaults.DEFAULT_DATABASE_PATH
        capture_preview_path: Path = defaults.DEFAULT_CAPTURE_PREVIEW_PATH
        rpg_maker_bridge_enabled: bool = defaults.DEFAULT_RPG_MAKER_BRIDGE_ENABLED
        rpg_maker_bridge_host: str = defaults.DEFAULT_RPG_MAKER_BRIDGE_HOST
        rpg_maker_bridge_port: int = defaults.DEFAULT_RPG_MAKER_BRIDGE_PORT
