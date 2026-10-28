"""Image preparation: cropping, tinting and resampling to the output resolution.

Source photos are often far larger than needed (4000+ px for a 6 cm slot).
Every image is resampled to the requested DPI for the size it is printed at
and opaque images are re-encoded as JPEG, which keeps the PDF light without
visible loss.
"""

from __future__ import annotations

import io
from enum import Enum
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

from .geometry import cover_crop

POINTS_PER_INCH = 72.0
SUBJECT_THRESHOLD = 200  # grey level below which a pixel belongs to the subject
EDGE_SAMPLE_COLUMNS = 8  # backdrop columns averaged when extending a photo
EDGE_SMOOTHING = 6  # px of blur along the averaged edge, to remove grain
SEAM_BLEND_RATIO = 0.06  # share of the photo width blended into the extension, per side
# Plain-backdrop test: mean detail (difference from a blurred copy, in grey levels)
# along the edges. Studio shots measure below 1, photos taken outdoors above 14.
BACKDROP_PROBE_WIDTH = 300  # px: the test runs on a small copy
BACKDROP_EDGE = 0.04  # share of the photo inspected along each edge
BACKDROP_MAX_DETAIL = 4.0


class Edge(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"


ALL_EDGES = frozenset(Edge)


class ImageLibrary:
    def __init__(self, assets_dir: Path, dpi: int, jpeg_quality: int = 88) -> None:
        if dpi <= 0:
            raise ValueError("dpi must be positive")
        self._assets_dir = assets_dir
        self._dpi = dpi
        self._jpeg_quality = jpeg_quality

    def size(self, path: Path) -> tuple[int, int]:
        """Pixel size of an asset, without decoding it."""
        with Image.open(self._assets_dir / path) as image:
            return image.size

    def fitted(self, path: Path, width_pt: float, height_pt: float) -> ImageReader:
        """The whole image, resampled for a ``width_pt`` x ``height_pt`` slot."""
        with Image.open(self._assets_dir / path) as image:
            return self._encode(self._resample(image, width_pt, height_pt))

    def on_white(
        self,
        path: Path,
        width_pt: float,
        height_pt: float,
        *,
        region: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
        white_point: int = 238,
        feather: float = 0.12,
    ) -> ImageReader:
        """A product shot prepared to be blended in multiply mode on a white page.

        Two steps make the studio backdrop vanish without a trace:
        - levels: every grey at or above ``white_point`` becomes pure white;
        - feather: the borders fade to white over ``feather`` of the shorter
          side, so a backdrop that is greyer near the edges (the studio floor)
          cannot reveal the rectangle of the photo.

        ``region`` (fractions l, t, r, b) crops the photo first, typically to
        the subject plus a margin: less flat backdrop to hide, lighter file.
        """
        with Image.open(self._assets_dir / path) as image:
            left, top, right, bottom = region
            box = (
                round(left * image.width),
                round(top * image.height),
                round(right * image.width),
                round(bottom * image.height),
            )
            photo = self._resample(image.crop(box), width_pt, height_pt)
        return self._encode(whitened(photo, white_point=white_point, feather=feather))

    def cropped(
        self, path: Path, width_pt: float, height_pt: float, focus_y: float = 0.5, focus_x: float = 0.5
    ) -> ImageReader:
        """The image cropped to fill a ``width_pt`` x ``height_pt`` slot entirely."""
        with Image.open(self._assets_dir / path) as image:
            box = cover_crop(image.width, image.height, width_pt / height_pt, focus_y, focus_x)
            return self._encode(self._resample(image.crop(box), width_pt, height_pt))

    def shaded(
        self,
        path: Path,
        width_pt: float,
        height_pt: float,
        *,
        strength: float,
        start: float = 0.5,
        focus_y: float = 0.5,
        focus_x: float = 0.5,
    ) -> ImageReader:
        """A full-bleed photo darkened towards the bottom, so light text can sit on it.

        Below ``start`` (a fraction of the height) the image darkens smoothly,
        reaching ``strength`` (0-1) at the bottom edge; the top is untouched.
        """
        with Image.open(self._assets_dir / path) as image:
            box = cover_crop(image.width, image.height, width_pt / height_pt, focus_y, focus_x)
            photo = self._resample(image.crop(box).convert("RGB"), width_pt, height_pt)
        ramp = Image.new("L", (1, photo.height))
        span = max(1.0, (1.0 - start) * photo.height)
        first = start * photo.height
        ramp.putdata(
            [
                round(255 * (1 - strength * min(1.0, max(0.0, (y - first) / span)) ** 1.4))
                for y in range(photo.height)
            ]
        )
        shade = ramp.resize(photo.size)
        black = Image.new("RGB", photo.size, (0, 0, 0))
        return self._encode(Image.composite(photo, black, shade))

    def bled(self, path: Path, width_pt: float, height_pt: float) -> ImageReader:
        """A studio photo filling a slot of a different shape, never cropping the subject.

        The missing space is added by extending the seamless backdrop:
        - slot wider than the photo: the photo keeps its full height and the
          backdrop is extended evenly on both sides;
        - slot taller than the photo: the photo keeps its full width and sits
          at the bottom of the slot, with the wall extended above it.
        """
        with Image.open(self._assets_dir / path) as source:
            image = source.convert("RGB")
        ratio = width_pt / height_pt
        target_width = round(image.height * ratio)
        if target_width >= image.width:
            canvas = _extend_sideways(image, target_width, first_share=0.5)
        else:
            # Same operation on the photo turned on its side: the top edge
            # becomes the left one, and all the new space goes there.
            turned = image.transpose(Image.Transpose.ROTATE_90)
            target_height = round(image.width / ratio)
            canvas = _extend_sideways(turned, target_height, first_share=1.0).transpose(
                Image.Transpose.ROTATE_270
            )
        return self._encode(self._resample(canvas, width_pt, height_pt))

    def filled(self, path: Path, width_pt: float, height_pt: float, focus_y: float = 0.5) -> ImageReader:
        """A photo filling a slot of any shape, whatever kind of photo it is.

        Studio shots keep the whole subject and get their backdrop extended
        (``bled``); photos taken in a real setting are cropped instead
        (``cropped``), since repeating rock or grass would show as streaks.
        Only the edges that ``bled`` would extend are inspected: a sole
        touching the right edge does not matter when only the top grows.
        """
        if self.has_plain_backdrop(path, self._extended_edges(path, width_pt / height_pt)):
            return self.bled(path, width_pt, height_pt)
        return self.cropped(path, width_pt, height_pt, focus_y)

    def has_plain_backdrop(self, path: Path, edges: frozenset[Edge] = ALL_EDGES) -> bool:
        """Whether the given edges of the photo are a smooth, seamless backdrop."""
        with Image.open(self._assets_dir / path) as source:
            ratio = source.height / source.width
            grey = source.convert("L").resize(
                (BACKDROP_PROBE_WIDTH, max(1, round(BACKDROP_PROBE_WIDTH * ratio)))
            )
        detail = ImageChops.difference(grey, grey.filter(ImageFilter.GaussianBlur(3)))
        w = max(1, round(grey.width * BACKDROP_EDGE))
        h = max(1, round(grey.height * BACKDROP_EDGE))
        strips = {
            Edge.LEFT: (0, 0, w, grey.height),
            Edge.RIGHT: (grey.width - w, 0, grey.width, grey.height),
            Edge.TOP: (0, 0, grey.width, h),
        }
        return all(_mean(detail.crop(strips[edge])) <= BACKDROP_MAX_DETAIL for edge in edges)

    def _extended_edges(self, path: Path, slot_ratio: float) -> frozenset[Edge]:
        """The edges ``bled`` extends to reach ``slot_ratio`` (see its two cases)."""
        width, height = self.size(path)
        if round(height * slot_ratio) >= width:
            return frozenset({Edge.LEFT, Edge.RIGHT})
        return frozenset({Edge.TOP})

    def luminance(self, path: Path, region: tuple[float, float, float, float]) -> float:
        """Mean grey level (0-255) of ``region`` (fractions l, t, r, b) of the photo."""
        with Image.open(self._assets_dir / path) as source:
            ratio = source.height / source.width
            grey = source.convert("L").resize(
                (BACKDROP_PROBE_WIDTH, max(1, round(BACKDROP_PROBE_WIDTH * ratio)))
            )
        left, top, right, bottom = region
        box = (
            round(left * grey.width),
            round(top * grey.height),
            max(round(right * grey.width), round(left * grey.width) + 1),
            max(round(bottom * grey.height), round(top * grey.height) + 1),
        )
        return _mean(grey.crop(box))

    def subject_bounds(self, path: Path) -> tuple[float, float, float, float]:
        """Box of the subject of a photo on a white backdrop, as fractions (l, t, r, b).

        Pixels noticeably darker than white count as subject; the result lets a
        layout place and scale the product itself rather than the whole frame.
        """
        with Image.open(self._assets_dir / path) as source:
            grey = source.convert("L")
        mask = grey.point(lambda v: 255 if v < SUBJECT_THRESHOLD else 0)
        box = mask.getbbox()
        if box is None:
            return 0.0, 0.0, 1.0, 1.0
        left, top, right, bottom = box
        return left / grey.width, top / grey.height, right / grey.width, bottom / grey.height

    def tinted(self, mask_path: Path, color: Color, width_pt: float, height_pt: float) -> ImageReader:
        """A solid ``color`` image whose alpha channel is the greyscale mask."""
        with Image.open(self._assets_dir / mask_path) as mask:
            alpha = self._resample(mask.convert("L"), width_pt, height_pt)
        rgb = tuple(round(channel * 255) for channel in color.rgb())
        tinted = Image.new("RGBA", alpha.size, (*rgb, 255))
        tinted.putalpha(alpha)
        return self._encode(tinted)

    def _resample(self, image: Image.Image, width_pt: float, height_pt: float) -> Image.Image:
        """Downscale to the target DPI; never upscale (it would only add bytes)."""
        target = (
            max(1, round(width_pt / POINTS_PER_INCH * self._dpi)),
            max(1, round(height_pt / POINTS_PER_INCH * self._dpi)),
        )
        if target[0] >= image.width or target[1] >= image.height:
            return image.copy()
        return image.resize(target, Image.Resampling.LANCZOS, reducing_gap=3.0)

    def _encode(self, image: Image.Image) -> ImageReader:
        buffer = io.BytesIO()
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            image.save(buffer, format="PNG", optimize=True)
        else:
            image.convert("RGB").save(buffer, format="JPEG", quality=self._jpeg_quality, optimize=True)
        buffer.seek(0)
        return ImageReader(buffer)


def whitened(photo: Image.Image, *, white_point: int = 238, feather: float = 0.12) -> Image.Image:
    """A studio shot whose backdrop becomes pure white, borders feathered to white (see ``on_white``)."""
    photo = photo.convert("RGB")
    scale = 255 / white_point
    photo = photo.point(lambda v: min(255, round(v * scale)))
    band = max(1, round(min(photo.size) * feather))
    mask = ImageChops.multiply(
        _edge_ramp(photo.width, band).resize(photo.size),
        _edge_ramp(photo.height, band).transpose(Image.Transpose.ROTATE_90).resize(photo.size),
    )
    white = Image.new("RGB", photo.size, (255, 255, 255))
    return Image.composite(photo, white, mask)


def _mean(image: Image.Image) -> float:
    histogram = image.histogram()
    return sum(level * count for level, count in enumerate(histogram)) / max(1, sum(histogram))


def _extend_sideways(image: Image.Image, target_width: int, first_share: float) -> Image.Image:
    """Widen ``image`` to ``target_width`` by extending its left and right backdrop.

    ``first_share`` of the new width goes to the left, the rest to the right.
    Each extension is pasted over the photo's outer band through a ramp mask,
    so details near the edges (a table edge, a shadow) fade into the flat
    backdrop instead of ending in a visible step.
    """
    extra = target_width - image.width
    if extra <= 0:
        return image
    pad_left = round(extra * first_share)
    pad_right = extra - pad_left
    blend = min(round(image.width * SEAM_BLEND_RATIO), image.width // 2)
    canvas = Image.new("RGB", (target_width, image.height))
    canvas.paste(image, (pad_left, 0))
    if pad_left:
        left = _backdrop_strip(image, left=True, width=pad_left + blend)
        canvas.paste(left, (0, 0), _ramp(left.width, image.height, blend, fade_right=True))
    if pad_right:
        right = _backdrop_strip(image, left=False, width=pad_right + blend)
        mask = _ramp(right.width, image.height, blend, fade_right=False)
        canvas.paste(right, (target_width - right.width, 0), mask)
    return canvas


def _backdrop_strip(image: Image.Image, *, left: bool, width: int) -> Image.Image:
    """``width`` columns repeating the averaged outer edge of ``image``.

    Averaging a few columns first removes sensor noise, which would otherwise
    turn into visible streaks once repeated.
    """
    sample = min(EDGE_SAMPLE_COLUMNS, image.width)
    x0 = 0 if left else image.width - sample
    edge = image.crop((x0, 0, x0 + sample, image.height)).resize((1, image.height), Image.Resampling.BOX)
    # Soften the strip along its length too: grain repeated across a wide
    # extension would show as fine stripes, while the backdrop's gradient stays.
    edge = edge.filter(ImageFilter.GaussianBlur(EDGE_SMOOTHING))
    return edge.resize((max(width, 1), image.height), Image.Resampling.NEAREST)


def _ramp(width: int, height: int, blend: int, *, fade_right: bool) -> Image.Image:
    """Mask that is opaque over the extension and fades to transparent over ``blend`` px."""
    solid = width - blend
    row = [255] * solid + [round(255 * (1 - (i + 1) / (blend + 1))) for i in range(blend)]
    if not fade_right:
        row.reverse()
    mask = Image.new("L", (width, 1))
    mask.putdata(row)
    return mask.resize((width, height), Image.Resampling.NEAREST)


def _edge_ramp(length: int, band: int) -> Image.Image:
    """A ``length`` x 1 mask: 0 at both ends, rising smoothly to 255 over ``band`` px."""

    def level(i: int) -> int:
        t = min(1.0, min(i, length - 1 - i) / band)
        return round(255 * t * t * (3 - 2 * t))  # smoothstep: no visible start of the fade

    ramp = Image.new("L", (length, 1))
    ramp.putdata([level(i) for i in range(length)])
    return ramp
