from live_translator.application.geometry import rectangles_overlap
from live_translator.domain.models import OverlayPlacement, TextRegion


def test_rectangles_overlap_when_regions_intersect():
    region = TextRegion(x=100, y=100, width=300, height=120)
    overlay = OverlayPlacement(x=250, y=150, width=400, height=80)

    assert rectangles_overlap(region, overlay) is True


def test_rectangles_do_not_overlap_when_edges_only_touch():
    region = TextRegion(x=100, y=100, width=300, height=120)
    overlay = OverlayPlacement(x=400, y=100, width=200, height=120)

    assert rectangles_overlap(region, overlay) is False


def test_rectangles_do_not_overlap_when_separated():
    region = TextRegion(x=100, y=100, width=300, height=120)
    overlay = OverlayPlacement(x=100, y=260, width=300, height=120)

    assert rectangles_overlap(region, overlay) is False
