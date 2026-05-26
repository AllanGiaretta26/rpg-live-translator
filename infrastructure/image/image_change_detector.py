from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .image_hasher import ImageHasher, hash_distance


Hasher = Callable[[object], str]


@dataclass(slots=True)
class ImageChangeDetector:
    threshold: int = 0
    hasher: Hasher = field(default_factory=lambda: ImageHasher().hash_image)
    _last_hash: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.threshold < 0:
            raise ValueError("threshold must be zero or greater")

    def reset(self) -> None:
        self._last_hash = None

    def has_changed(self, image: object) -> bool:
        current_hash = self.hasher(image)

        if self._last_hash is None:
            self._last_hash = current_hash
            return True

        distance = hash_distance(self._last_hash, current_hash)
        changed = distance > self.threshold
        self._last_hash = current_hash
        return changed

