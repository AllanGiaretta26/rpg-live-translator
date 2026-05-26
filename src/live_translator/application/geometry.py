from __future__ import annotations

from live_translator.domain.models import OverlayPlacement, TextRegion


def rectangles_overlap(region: TextRegion, overlay: OverlayPlacement) -> bool:
    region_right = region.x + region.width
    region_bottom = region.y + region.height
    overlay_right = overlay.x + overlay.width
    overlay_bottom = overlay.y + overlay.height

    return (
        region.x < overlay_right
        and region_right > overlay.x
        and region.y < overlay_bottom
        and region_bottom > overlay.y
    )
