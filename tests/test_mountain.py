from __future__ import annotations

from monpiz_lookbook.mountain import MASSIF, Facet, Tone, place


def test_place_scales_and_offsets_every_point() -> None:
    facet = Facet(Tone.ROCK, ((0.0, 0.0), (100.0, 50.0)))
    (placed,) = place((facet,), x=10.0, top=20.0, scale=0.5)
    assert placed.points == ((10.0, 20.0), (60.0, 45.0))
    assert placed.tone is Tone.ROCK


def test_massif_is_drawn_from_the_silhouette_up() -> None:
    assert MASSIF[0].tone is Tone.ROCK  # base silhouette first, details painted over it
