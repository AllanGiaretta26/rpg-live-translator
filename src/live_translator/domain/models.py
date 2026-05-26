from __future__ import annotations

from dataclasses import dataclass


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
