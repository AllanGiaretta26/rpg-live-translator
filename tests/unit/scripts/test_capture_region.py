from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from domain.models import TextRegion
from scripts.capture_region import _region_from_args


def test_region_from_args_returns_none_when_no_coordinates_are_given():
    args = Namespace(x=None, y=None, width=None, height=None)

    assert _region_from_args(args) is None


def test_region_from_args_requires_complete_coordinates():
    args = Namespace(x=1, y=None, width=3, height=4)

    with pytest.raises(ValueError, match="provided together"):
        _region_from_args(args)


def test_region_from_args_builds_text_region():
    args = Namespace(x=1, y=2, width=3, height=4)

    assert _region_from_args(args) == TextRegion(x=1, y=2, width=3, height=4)
