"""Pure layout helpers, independent of ReportLab and therefore unit-testable.

Coordinates follow the design convention: origin at the top-left corner of
the page, y growing downwards, units in points.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import combinations_with_replacement, pairwise


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    top: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    def inset(self, dx: float, dy: float | None = None) -> Box:
        dy = dx if dy is None else dy
        return Box(self.x + dx, self.top + dy, self.width - 2 * dx, self.height - 2 * dy)


def contain(src_w: float, src_h: float, box: Box) -> Box:
    """Largest box with the source aspect ratio that fits ``box``, centred in it."""
    scale = min(box.width / src_w, box.height / src_h)
    width, height = src_w * scale, src_h * scale
    return Box(
        box.x + (box.width - width) / 2,
        box.top + (box.height - height) / 2,
        width,
        height,
    )


def cover_crop(
    src_w: int, src_h: int, target_ratio: float, focus_y: float = 0.5
) -> tuple[int, int, int, int]:
    """Pixel crop (left, top, right, bottom) giving ``target_ratio`` (width/height).

    The crop keeps the full extent along one axis and is centred horizontally;
    vertically it is positioned by ``focus_y`` (0 = top, 1 = bottom).
    """
    if src_w / src_h > target_ratio:
        width = round(src_h * target_ratio)
        left = (src_w - width) // 2
        return left, 0, left + width, src_h
    height = round(src_w / target_ratio)
    top = round((src_h - height) * focus_y)
    return 0, top, src_w, top + height


def wrap_text(text: str, measure: Callable[[str], float], width: float) -> list[str]:
    """Greedy word wrap. Explicit newlines in ``text`` are preserved.

    A single word wider than ``width`` is kept on its own line rather than
    being broken: catalogue copy never needs hyphenation.
    """
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if current and measure(candidate) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def balance_columns(heights: Sequence[float], columns: int) -> list[range]:
    """Split ordered blocks into ``columns`` contiguous groups minimising the tallest.

    Returns one ``range`` of block indices per column (possibly empty).
    Exhaustive search over split points: the number of blocks on a page is
    small enough that an optimal answer costs nothing.
    """
    if columns < 1:
        raise ValueError("columns must be >= 1")
    count = len(heights)
    best: list[range] | None = None
    best_height = float("inf")
    for cuts in combinations_with_replacement(range(count + 1), columns - 1):
        bounds = (0, *cuts, count)
        groups = [range(a, b) for a, b in pairwise(bounds)]
        tallest = max(sum(heights[i] for i in group) for group in groups)
        if tallest < best_height:
            best, best_height = groups, tallest
    assert best is not None
    return best
