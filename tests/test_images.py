from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from monpiz_lookbook.images import ImageLibrary


@pytest.fixture
def studio_photo(tmp_path: Path) -> Path:
    """A 300x200 'studio shot': grey backdrop with a dark subject in the middle."""
    image = Image.new("RGB", (300, 200), (200, 200, 200))
    image.paste((20, 20, 20), (100, 60, 200, 180))
    image.save(tmp_path / "shot.png")
    return Path("shot.png")


@pytest.mark.parametrize(("width_pt", "height_pt"), [(600.0, 200.0), (300.0, 600.0)])
def test_bled_fills_slots_wider_or_taller_than_the_photo(
    tmp_path: Path, studio_photo: Path, width_pt: float, height_pt: float
) -> None:
    library = ImageLibrary(tmp_path, dpi=72)
    width, height = library.bled(studio_photo, width_pt, height_pt).getSize()
    assert width / height == pytest.approx(width_pt / height_pt, rel=0.01)


def test_bled_keeps_the_subject_whole_in_a_tall_slot(tmp_path: Path, studio_photo: Path) -> None:
    # The photo keeps its full width and sits at the bottom: the subject stays
    # intact and the new space above it is backdrop only.
    reader = ImageLibrary(tmp_path, dpi=72).bled(studio_photo, 300.0, 600.0)
    width, height = reader.getSize()
    image = Image.frombytes("RGB", (width, height), reader.getRGBData())
    assert image.getpixel((150, height - 80)) == (20, 20, 20)  # subject, near the bottom
    backdrop = image.getpixel((150, 50))
    assert isinstance(backdrop, tuple)
    assert backdrop[0] > 150  # extended backdrop above


def test_on_white_turns_a_grey_backdrop_white_and_keeps_the_subject(tmp_path: Path) -> None:
    # A studio shot whose backdrop is not quite white (as a studio floor often is).
    image = Image.new("RGB", (300, 200), (232, 232, 232))
    image.paste((20, 20, 20), (100, 60, 200, 180))
    image.save(tmp_path / "grey.png")

    reader = ImageLibrary(tmp_path, dpi=72).on_white(Path("grey.png"), 300.0, 200.0)
    width, height = reader.getSize()
    result = Image.frombytes("RGB", (width, height), reader.getRGBData())
    corner, subject = result.getpixel((2, 2)), result.getpixel((150, 120))
    assert isinstance(corner, tuple) and isinstance(subject, tuple)
    assert min(corner) >= 253  # backdrop and borders vanish in multiply mode
    assert max(subject) <= 40  # the product itself is untouched
