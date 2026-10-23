from __future__ import annotations

from monpiz_lookbook.mountain import BOX_HEIGHT, BOX_WIDTH, SKYLINE, SPINES, place


def test_place_scales_and_offsets_every_point() -> None:
    assert place(((0.0, 0.0), (100.0, 50.0)), x=10.0, top=20.0, scale=0.5) == [(10.0, 20.0), (60.0, 45.0)]


def test_skyline_spans_the_box_from_left_to_right() -> None:
    xs = [x for x, _ in SKYLINE]
    assert xs == sorted(xs)
    assert (xs[0], xs[-1]) == (0, BOX_WIDTH)
    assert all(0 <= y <= BOX_HEIGHT for _, y in SKYLINE)


def test_every_spine_starts_on_a_summit_of_the_skyline() -> None:
    for spine in SPINES:
        assert spine[0] in SKYLINE
