from __future__ import annotations

from dataclasses import dataclass

from infrastructure.image.image_hasher import ImageHasher, hash_distance


@dataclass
class MemoryImage:
    size: tuple[int, int]
    pixels: list[tuple[int, int, int] | int]

    def getdata(self):
        return tuple(self.pixels)


def build_half_and_half_image(left_value: int, right_value: int) -> MemoryImage:
    pixels: list[tuple[int, int, int]] = []
    for _y in range(8):
        for x in range(8):
            value = left_value if x < 4 else right_value
            pixels.append((value, value, value))
    return MemoryImage(size=(8, 8), pixels=pixels)


def test_hash_is_stable_for_identical_images():
    hasher = ImageHasher()
    image = build_half_and_half_image(0, 255)

    assert hasher.hash_image(image) == hasher.hash_image(image)


def test_hash_distance_detects_structural_difference():
    hasher = ImageHasher()
    left_to_right = build_half_and_half_image(0, 255)
    right_to_left = build_half_and_half_image(255, 0)

    left_hash = hasher.hash_image(left_to_right)
    right_hash = hasher.hash_image(right_to_left)

    assert left_hash != right_hash
    assert hash_distance(left_hash, right_hash) == 64


def test_hash_distance_counts_bit_changes():
    assert hash_distance("0000000000000000", "0000000000000003") == 2

