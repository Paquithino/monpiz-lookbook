"""Image preparation: cropping, tinting and resampling to the output resolution.

Source photos are often far larger than needed (4000+ px for a 6 cm slot).
Every image is resampled to the requested DPI for the size it is printed at
and opaque images are re-encoded as JPEG, which keeps the PDF light without
visible loss.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageFilter
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

from .geometry import cover_crop

POINTS_PER_INCH = 72.0
SUBJECT_THRESHOLD = 200  # grey level below which a pixel belongs to the subject
EDGE_SAMPLE_COLUMNS = 8  # backdrop columns averaged when extending a photo
EDGE_SMOOTHING = 6  # px of blur along the averaged edge, to remove grain
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

    def fitted(
        self, path: Path, width_pt: float, height_pt: float, *, white_point: int | None = None
    ) -> ImageReader:
        """The whole image, resampled for a ``width_pt`` x ``height_pt`` slot.

        ``white_point`` stretches the levels so that every grey at or above it
        becomes pure white: a studio backdrop that is almost white turns fully
        white, which matters when the image is blended in multiply mode.
        """
        with Image.open(self._assets_dir / path) as image:
            resampled = self._resample(image, width_pt, height_pt)
        if white_point is not None:
            scale = 255 / white_point
            resampled = resampled.convert("RGB").point(lambda v: min(255, round(v * scale)))
        return self._encode(resampled)

    def cropped(self, path: Path, width_pt: float, height_pt: float, focus_y: float = 0.5) -> ImageReader:
        """The image cropped to fill a ``width_pt`` x ``height_pt`` slot entirely."""
        with Image.open(self._assets_dir / path) as image:
            box = cover_crop(image.width, image.height, width_pt / height_pt, focus_y)
            return self._encode(self._resample(image.crop(box), width_pt, height_pt))

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
