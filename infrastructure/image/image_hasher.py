from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def _normalize_pixel(pixel: object) -> int:
    if isinstance(pixel, int):
        return max(0, min(255, pixel))

    if isinstance(pixel, Sequence):
        if not pixel:
            return 0

        red = int(pixel[0])
        green = int(pixel[1]) if len(pixel) > 1 else red
        blue = int(pixel[2]) if len(pixel) > 2 else red
        return max(
            0,
            min(
                255,
                int(round(0.299 * red + 0.587 * green + 0.114 * blue)),
            ),
        )

    raise TypeError(f"Unsupported pixel value: {pixel!r}")


def _require_image_size(image: object) -> tuple[int, int]:
    if not hasattr(image, "size"):
        raise TypeError("image must expose a size attribute")

    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("image size must be greater than zero")
    return int(width), int(height)


def _extract_grayscale_pixels(image: object) -> tuple[int, int, list[int]]:
    width, height = _require_image_size(image)

    if not hasattr(image, "getdata"):
        raise TypeError("image must expose a getdata() method")

    pixels = [_normalize_pixel(pixel) for pixel in image.getdata()]
    expected_length = width * height
    if len(pixels) != expected_length:
        raise ValueError(
            f"image data length {len(pixels)} does not match {expected_length}"
        )
    return width, height, pixels


def _resize_nearest(
    pixels: list[int],
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
) -> list[int]:
    if target_width <= 0 or target_height <= 0:
        raise ValueError("target size must be greater than zero")

    resized: list[int] = []
    for y in range(target_height):
        source_y = min(source_height - 1, int(y * source_height / target_height))
        for x in range(target_width):
            source_x = min(source_width - 1, int(x * source_width / target_width))
            resized.append(pixels[source_y * source_width + source_x])
    return resized


def hash_distance(left_hash: str, right_hash: str) -> int:
    left_value = int(left_hash, 16)
    right_value = int(right_hash, 16)
    return (left_value ^ right_value).bit_count()


@dataclass(frozen=True, slots=True)
class ImageHasher:
    hash_size: int = 8

    def hash_image(self, image: object) -> str:
        if self.hash_size <= 0:
            raise ValueError("hash_size must be greater than zero")

        width, height, pixels = _extract_grayscale_pixels(image)
        resized = _resize_nearest(pixels, width, height, self.hash_size, self.hash_size)
        average = sum(resized) / len(resized)

        bits = 0
        for pixel in resized:
            bits = (bits << 1) | int(pixel > average)

        hex_width = (self.hash_size * self.hash_size + 3) // 4
        return f"{bits:0{hex_width}x}"
