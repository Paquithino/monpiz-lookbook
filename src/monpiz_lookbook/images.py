"""Image preparation: cropping, tinting and resampling to the output resolution.

Source photos are often far larger than needed (4000+ px for a 6 cm slot).
Every image is resampled to the requested DPI for the size it is printed at
and opaque images are re-encoded as JPEG, which keeps the PDF light without
visible loss.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

from .geometry import cover_crop

POINTS_PER_INCH = 72.0
FADE_STEPS = 512
EDGE_SAMPLE_COLUMNS = 8  # backdrop columns averaged when extending a photo
SEAM_BLEND_RATIO = 0.06  # share of the photo width blended into the extension, per side


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

    def cropped(self, path: Path, width_pt: float, height_pt: float, focus_y: float = 0.5) -> ImageReader:
        """The image cropped to fill a ``width_pt`` x ``height_pt`` slot entirely."""
        with Image.open(self._assets_dir / path) as image:
            box = cover_crop(image.width, image.height, width_pt / height_pt, focus_y)
            return self._encode(self._resample(image.crop(box), width_pt, height_pt))

    def bled(self, path: Path, width_pt: float, height_pt: float) -> ImageReader:
        """A studio photo filling a slot wider than itself, without cropping the subject.

        The photo keeps its full height; the missing width is added on both
        sides by extending the backdrop (the averaged outermost columns), which
        is invisible on a seamless studio background. A photo wider than the
        slot is cropped horizontally around its centre instead.
        """
        with Image.open(self._assets_dir / path) as source:
            image = source.convert("RGB")
        target_width = round(image.height * width_pt / height_pt)
        if target_width <= image.width:
            box = cover_crop(image.width, image.height, width_pt / height_pt)
            return self._encode(self._resample(image.crop(box), width_pt, height_pt))

        pad_left = (target_width - image.width) // 2
        pad_right = target_width - image.width - pad_left
        blend = min(round(image.width * SEAM_BLEND_RATIO), image.width // 2)
        left = _backdrop_strip(image, left=True, width=pad_left + blend)
        right = _backdrop_strip(image, left=False, width=pad_right + blend)
        canvas = Image.new("RGB", (target_width, image.height))
        canvas.paste(image, (pad_left, 0))
        # Paste the extensions over the photo's outer band through a ramp mask,
        # so details near the edges (a table edge, a shadow) fade into the
        # flat backdrop instead of ending in a visible step.
        canvas.paste(left, (0, 0), _ramp(left.width, image.height, blend, fade_right=True))
        canvas.paste(
            right, (target_width - right.width, 0), _ramp(right.width, image.height, blend, fade_right=False)
        )
        return self._encode(self._resample(canvas, width_pt, height_pt))

    def tinted(self, mask_path: Path, color: Color, width_pt: float, height_pt: float) -> ImageReader:
        """A solid ``color`` image whose alpha channel is the greyscale mask."""
        with Image.open(self._assets_dir / mask_path) as mask:
            alpha = self._resample(mask.convert("L"), width_pt, height_pt)
        rgb = tuple(round(channel * 255) for channel in color.rgb())
        tinted = Image.new("RGBA", alpha.size, (*rgb, 255))
        tinted.putalpha(alpha)
        return self._encode(tinted)

    def vertical_fade(self, color: Color, start: float, end_alpha: float) -> ImageReader:
        """Overlay of ``color``: transparent above ``start`` (0-1 of the height),
        then a linear ramp to ``end_alpha`` at the bottom.

        It is a 1-pixel-wide ramp meant to be stretched over its box: being
        constant horizontally, stretching it introduces no artefacts.
        """
        steps = FADE_STEPS
        ramp = Image.new("L", (1, steps))
        for row in range(steps):
            position = (row / (steps - 1) - start) / (1 - start)
            ramp.putpixel((0, row), round(255 * end_alpha * min(max(position, 0.0), 1.0)))
        rgb = tuple(round(channel * 255) for channel in color.rgb())
        overlay = Image.new("RGBA", ramp.size, (*rgb, 255))
        overlay.putalpha(ramp)
        return self._encode(overlay)

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


def _backdrop_strip(image: Image.Image, *, left: bool, width: int) -> Image.Image:
    """``width`` columns repeating the averaged outer edge of ``image``.

    Averaging a few columns first removes sensor noise, which would otherwise
    turn into visible horizontal streaks once repeated.
    """
    sample = min(EDGE_SAMPLE_COLUMNS, image.width)
    x0 = 0 if left else image.width - sample
    edge = image.crop((x0, 0, x0 + sample, image.height)).resize((1, image.height), Image.Resampling.BOX)
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
