from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OperationMode(str, Enum):
    UNIVERSAL = "universal"
    RPG_MAKER_MV_MZ = "rpg_maker_mv_mz"


class RpgMakerVersion(str, Enum):
    MV = "MV"
    MZ = "MZ"
    MV_MZ = "MV/MZ"


class RpgMakerTextType(str, Enum):
    MESSAGE = "message"
    SPEAKER = "speaker"
    CHOICE = "choice"
    SCROLLING_TEXT = "scrolling_text"
    ITEM_NAME = "item_name"
    ITEM_DESCRIPTION = "item_description"
    SKILL_NAME = "skill_name"
    SKILL_DESCRIPTION = "skill_description"
    SKILL_MESSAGE = "skill_message"
    WEAPON_NAME = "weapon_name"
    WEAPON_DESCRIPTION = "weapon_description"
    ARMOR_NAME = "armor_name"
    ARMOR_DESCRIPTION = "armor_description"
    STATE_NAME = "state_name"
    STATE_MESSAGE = "state_message"
    CLASS_NAME = "class_name"
    ENEMY_NAME = "enemy_name"
    ACTOR_NAME = "actor_name"
    SYSTEM_TERM = "system_term"
    TROOP_MESSAGE = "troop_message"
    TROOP_CHOICE = "troop_choice"
    TROOP_SCROLLING_TEXT = "troop_scrolling_text"
    TROOP_SPEAKER = "troop_speaker"


@dataclass(frozen=True)
class TextRegion:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be greater than zero")
        if self.height <= 0:
            raise ValueError("height must be greater than zero")
        if self.x < 0:
            raise ValueError("x must be zero or greater")
        if self.y < 0:
            raise ValueError("y must be zero or greater")


@dataclass(frozen=True)
class ExtractedText:
    text: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.confidence is None:
            return
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class TranslationResult:
    source_text: str
    translated_text: str
    source_lang: str = "auto"
    target_lang: str = "pt-BR"

    def __post_init__(self) -> None:
        if not self.source_text.strip():
            raise ValueError("source_text must not be blank")
        if not self.translated_text.strip():
            raise ValueError("translated_text must not be blank")
        if not self.source_lang.strip():
            raise ValueError("source_lang must not be blank")
        if not self.target_lang.strip():
            raise ValueError("target_lang must not be blank")


@dataclass(frozen=True)
class GameProfile:
    name: str
    window_title: str
    text_region: TextRegion

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be blank")
        if not self.window_title.strip():
            raise ValueError("window_title must not be blank")


@dataclass(frozen=True)
class OverlayPlacement:
    x: int
    y: int
    width: int
    height: int
    opacity: float = 0.85
    font_size: int = 24

    def __post_init__(self) -> None:
        if self.x < 0:
            raise ValueError("x must be zero or greater")
        if self.y < 0:
            raise ValueError("y must be zero or greater")
        if self.width <= 0:
            raise ValueError("width must be greater than zero")
        if self.height <= 0:
            raise ValueError("height must be greater than zero")
        if not 0.0 < self.opacity <= 1.0:
            raise ValueError("opacity must be greater than zero and at most one")
        if self.font_size <= 0:
            raise ValueError("font_size must be greater than zero")


@dataclass(frozen=True)
class RpgMakerProject:
    root_path: Path
    data_path: Path
    version: RpgMakerVersion

    def __post_init__(self) -> None:
        if not self.root_path:
            raise ValueError("root_path must not be blank")
        if not self.data_path:
            raise ValueError("data_path must not be blank")


@dataclass(frozen=True)
class RpgMakerTextOrigin:
    file_name: str
    origin_key: str
    map_id: int | None = None
    event_id: int | None = None
    page_index: int | None = None
    command_index: int | None = None
    parameter_index: int | None = None
    database_id: int | None = None
    field_name: str | None = None

    def __post_init__(self) -> None:
        if not self.file_name.strip():
            raise ValueError("file_name must not be blank")
        if not self.origin_key.strip():
            raise ValueError("origin_key must not be blank")
        if self.database_id is not None and self.database_id <= 0:
            raise ValueError("database_id must be greater than zero")
        if self.field_name is not None and not self.field_name.strip():
            raise ValueError("field_name must not be blank")


@dataclass(frozen=True)
class RpgMakerTextEntry:
    source_text: str
    text_type: RpgMakerTextType
    origin: RpgMakerTextOrigin
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.source_text.strip():
            raise ValueError("source_text must not be blank")


@dataclass(frozen=True)
class RpgMakerImportResult:
    project: RpgMakerProject
    imported_count: int

    def __post_init__(self) -> None:
        if self.imported_count < 0:
            raise ValueError("imported_count must be zero or greater")


@dataclass(frozen=True)
class CatalogTranslationError:
    entry_id: int | None
    origin: str
    source_text: str
    error_message: str
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.entry_id is not None and self.entry_id <= 0:
            raise ValueError("entry_id must be greater than zero")
        if not self.origin.strip():
            raise ValueError("origin must not be blank")
        if not self.source_text.strip():
            raise ValueError("source_text must not be blank")
        if not self.error_message.strip():
            raise ValueError("error_message must not be blank")
