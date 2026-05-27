from __future__ import annotations

from dataclasses import dataclass

from live_translator.infrastructure.image.image_preprocessor import ImagePreprocessor


@dataclass
class MemoryImage:
    mode: str
    size: tuple[int, int]
    pixels: list[tuple[int, int, int] | int]

    def copy(self) -> "MemoryImage":
        return MemoryImage(self.mode, self.size, list(self.pixels))

    def getdata(self):
        return tuple(self.pixels)

    def convert(self, mode: str) -> "MemoryImage":
        if mode == self.mode:
            return self.copy()

        if mode == "L" and self.mode == "RGB":
            grayscale_pixels = []
            for red, green, blue in self.pixels:
                grayscale_pixels.append(
                    int(round(0.299 * red + 0.587 * green + 0.114 * blue))
                )
            return MemoryImage(mode="L", size=self.size, pixels=grayscale_pixels)

        if mode == "RGB" and self.mode == "L":
            rgb_pixels = [(pixel, pixel, pixel) for pixel in self.pixels]
            return MemoryImage(mode="RGB", size=self.size, pixels=rgb_pixels)

        raise ValueError(f"Unsupported conversion: {self.mode!r} -> {mode!r}")

    def resize(self, size: tuple[int, int]) -> "MemoryImage":
        target_width, target_height = size
        source_width, source_height = self.size
        resized_pixels: list[tuple[int, int, int] | int] = []

        for y in range(target_height):
            source_y = min(source_height - 1, int(y * source_height / target_height))
            for x in range(target_width):
                source_x = min(source_width - 1, int(x * source_width / target_width))
                resized_pixels.append(
                    self.pixels[source_y * source_width + source_x]
                )

        return MemoryImage(mode=self.mode, size=size, pixels=resized_pixels)

    def adjust_contrast(self, factor: float) -> "MemoryImage":
        if factor <= 0:
            raise ValueError("factor must be greater than zero")

        if self.mode == "RGB":
            channel_pixels = list(self.pixels)
            channels = list(zip(*channel_pixels, strict=True))
            adjusted_channels = []
            for channel in channels:
                mean = sum(channel) / len(channel)
                adjusted_channels.append(
                    [max(0, min(255, int(round((value - mean) * factor + mean)))) for value in channel]
                )
            adjusted_pixels = list(zip(*adjusted_channels, strict=True))
            return MemoryImage(mode="RGB", size=self.size, pixels=list(adjusted_pixels))

        mean = sum(self.pixels) / len(self.pixels)
        adjusted_pixels = [
            max(0, min(255, int(round((value - mean) * factor + mean))))
            for value in self.pixels
        ]
        return MemoryImage(mode=self.mode, size=self.size, pixels=adjusted_pixels)


def test_preprocessor_scales_image_using_nearest_neighbor():
    image = MemoryImage(
        mode="L",
        size=(2, 2),
        pixels=[10, 20, 30, 40],
    )
    preprocessor = ImagePreprocessor(scale_factor=2.0, contrast_factor=1.0)

    processed = preprocessor.process(image)

    assert processed.size == (4, 4)
    assert processed.mode == "L"
    assert processed.getdata() == (
        10,
        10,
        20,
        20,
        10,
        10,
        20,
        20,
        30,
        30,
        40,
        40,
        30,
        30,
        40,
        40,
    )


def test_preprocessor_can_convert_to_grayscale_and_adjust_contrast():
    image = MemoryImage(
        mode="RGB",
        size=(2, 1),
        pixels=[(20, 20, 20), (220, 220, 220)],
    )
    preprocessor = ImagePreprocessor(scale_factor=1.0, contrast_factor=2.0)

    processed = preprocessor.process(image)

    assert processed.mode == "L"
    assert processed.size == (2, 1)
    assert processed.getdata() == (0, 255)
