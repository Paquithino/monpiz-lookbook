from __future__ import annotations

import pytest

from monpiz_lookbook.geometry import Box, contain, cover_crop, wrap_text


def test_contain_centres_a_wide_image_in_a_square_box() -> None:
    fitted = contain(200, 100, Box(0, 0, 100, 100))
    assert fitted == Box(0, 25, 100, 50)


def test_cover_crop_keeps_full_height_for_a_wider_source() -> None:
    assert cover_crop(400, 100, 2.0) == (100, 0, 300, 100)


@pytest.mark.parametrize(("focus_y", "expected_top"), [(0.0, 0), (0.5, 50), (1.0, 100)])
def test_cover_crop_moves_vertically_with_focus(focus_y: float, expected_top: int) -> None:
    left, top, right, bottom = cover_crop(100, 200, 1.0, focus_y)
    assert (left, right, bottom - top) == (0, 100, 100)
    assert top == expected_top


def test_wrap_text_breaks_greedily_and_keeps_explicit_newlines() -> None:
    measure = len  # one unit per character
    assert wrap_text("aa bb cc\ndd", measure, 5) == ["aa bb", "cc", "dd"]


def test_wrap_text_never_splits_a_word_longer_than_the_width() -> None:
    assert wrap_text("abcdefgh ij", len, 4) == ["abcdefgh", "ij"]
