from __future__ import annotations

from dataclasses import dataclass

try:  # pragma: no cover - Pillow é opcional no ambiente de testes.
    from PIL import Image as PILImage  # type: ignore
    from PIL import ImageEnhance  # type: ignore
except ImportError:  # pragma: no cover - Pillow é opcional.
    PILImage = None
    ImageEnhance = None


def _scaled_size(width: int, height: int, scale_factor: float) -> tuple[int, int]:
    if scale_factor <= 0:
        raise ValueError("scale_factor must be greater than zero")

    scaled_width = max(1, int(round(width * scale_factor)))
    scaled_height = max(1, int(round(height * scale_factor)))
    return scaled_width, scaled_height


@dataclass(frozen=True, slots=True)
class ImagePreprocessor:
    scale_factor: float = 1.0
    contrast_factor: float = 1.0
    to_grayscale: bool = True

    def process(self, image: object) -> object:
        if self.scale_factor <= 0:
            raise ValueError("scale_factor must be greater than zero")
        if self.contrast_factor <= 0:
            raise ValueError("contrast_factor must be greater than zero")

        if self._is_noop():
            return self._copy(image)

        if self._is_pillow_image(image):
            return self._process_with_pillow(image)

        return self._process_generic(image)

    def _is_noop(self) -> bool:
        return (
            self.scale_factor == 1.0
            and self.contrast_factor == 1.0
            and self.to_grayscale is False
        )

    def _copy(self, image: object) -> object:
        if hasattr(image, "copy"):
            return image.copy()
        return image

    def _is_pillow_image(self, image: object) -> bool:
        return PILImage is not None and isinstance(image, PILImage.Image)

    def _process_with_pillow(self, image: object) -> object:
        processed = image.copy()

        if self.to_grayscale:
            processed = processed.convert("L")

        if self.scale_factor != 1.0:
            width, height = processed.size
            processed = processed.resize(_scaled_size(width, height, self.scale_factor))

        if self.contrast_factor != 1.0:
            processed = ImageEnhance.Contrast(processed).enhance(self.contrast_factor)

        return processed

    def _process_generic(self, image: object) -> object:
        processed = self._copy(image)

        if self.to_grayscale:
            if not hasattr(processed, "convert"):
                raise TypeError("image must expose convert() for grayscale processing")
            processed = processed.convert("L")

        if self.scale_factor != 1.0:
            if not hasattr(processed, "resize"):
                raise TypeError("image must expose resize() for scaling")
            width, height = processed.size
            processed = processed.resize(_scaled_size(width, height, self.scale_factor))

        if self.contrast_factor != 1.0:
            if hasattr(processed, "adjust_contrast"):
                processed = processed.adjust_contrast(self.contrast_factor)
            else:
                raise TypeError(
                    "image must expose adjust_contrast() for contrast processing"
                )

        return processed

