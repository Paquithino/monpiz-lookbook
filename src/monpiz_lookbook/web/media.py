"""Images of the digital edition: responsive WebP renditions.

Every photo is published at a few widths (a ``srcset``) so a phone downloads
a small file and a desktop screen a sharp one. File names carry a hash of the
source bytes and of the rendering parameters: a rebuild reuses what is already
on disk, and a changed photo gets a new name, so browsers never show a stale
copy from their cache.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from .text import slugify

WIDTHS = (480, 800, 1200, 1800)
QUALITY = 80
BACKDROP_BAND = 0.03  # share of the photo edges averaged to find its backdrop colour
IMAGE_DIR = "img"
MANIFEST = "manifest.json"


@dataclass(frozen=True, slots=True)
class Picture:
    """A published image: what an ``<img>`` element needs."""

    src: str  # the largest rendition, for browsers without srcset
    srcset: str
    width: int  # intrinsic size of the largest rendition (reserves space before loading)
    height: int
    backdrop: str  # CSS colour of the photo edges, to extend studio shots seamlessly


class WebImages:
    def __init__(self, assets_dir: Path, site_dir: Path) -> None:
        self._assets_dir = assets_dir
        self._out_dir = site_dir / IMAGE_DIR
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[tuple[object, ...], Picture] = {}
        self.written: set[Path] = set()  # every file of this build, to prune the others
        # Size and backdrop of every rendered image, so a rebuild need not open the photos again.
        self._manifest_path = self._out_dir / MANIFEST
        try:
            self._manifest: dict[str, dict[str, object]] = json.loads(self._manifest_path.read_text())
        except (FileNotFoundError, ValueError):
            self._manifest = {}
        self._used: dict[str, dict[str, object]] = {}

    def picture(
        self,
        path: Path,
        *,
        widths: Sequence[int] = WIDTHS,
        ratio: float | None = None,
        focus: tuple[float, float] = (0.5, 0.5),
        prepare: tuple[str, Callable[[Image.Image], Image.Image]] | None = None,
    ) -> Picture:
        """Renditions of ``path``, cropped to ``ratio`` (width / height) around ``focus`` if given.

        ``prepare`` is a named transformation applied first (the name enters the file hash).
        """
        key = (path, tuple(widths), ratio, focus, prepare[0] if prepare else None)
        if key not in self._cache:
            self._cache[key] = self._render(path, widths, ratio, focus, prepare)
        return self._cache[key]

    def prune(self) -> int:
        """Delete renditions no longer used by the content and save the manifest; returns how many."""
        self._manifest_path.write_text(json.dumps(self._used, indent=1, sort_keys=True))
        self.written.add(self._manifest_path)
        stale = [p for p in self._out_dir.iterdir() if p.is_file() and p not in self.written]
        for path in stale:
            path.unlink()
        return len(stale)

    def _render(
        self,
        path: Path,
        widths: Sequence[int],
        ratio: float | None,
        focus: tuple[float, float],
        prepare: tuple[str, Callable[[Image.Image], Image.Image]] | None,
    ) -> Picture:
        source = self._assets_dir / path
        digest = hashlib.sha1(source.read_bytes())
        digest.update(repr((QUALITY, ratio, focus, prepare[0] if prepare else None)).encode())
        stem = f"{slugify(path.stem)}-{digest.hexdigest()[:10]}"
        known = self._manifest.get(stem)
        if known is not None:
            files = [self._out_dir / f"{stem}-{w}.webp" for w in known["sizes"]]  # type: ignore[attr-defined]
            if known["widths"] == list(widths) and all(f.exists() for f in files):
                self.written.update(files)
                self._used[stem] = known
                return self._picture(stem, known)

        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image = image.convert("RGBA" if _has_alpha(image) else "RGB")
        if prepare is not None:
            image = prepare[1](image)
        if ratio is not None:
            image = _crop(image, ratio, focus)
        backdrop = _backdrop(image)

        sizes = sorted({min(w, image.width) for w in widths})
        for width in sizes:
            target = self._out_dir / f"{stem}-{width}.webp"
            self.written.add(target)
            if not target.exists():
                height = round(image.height * width / image.width)
                resized = image.resize((width, height), Image.Resampling.LANCZOS, reducing_gap=3.0)
                resized.save(target, format="WEBP", quality=QUALITY, method=6)
        info: dict[str, object] = {
            "widths": list(widths),
            "sizes": sizes,
            "height": round(image.height * sizes[-1] / image.width),
            "backdrop": backdrop,
        }
        self._used[stem] = info
        return self._picture(stem, info)

    @staticmethod
    def _picture(stem: str, info: dict[str, object]) -> Picture:
        sizes: list[int] = info["sizes"]  # type: ignore[assignment]
        urls = [(f"{IMAGE_DIR}/{stem}-{w}.webp", w) for w in sizes]
        return Picture(
            src=urls[-1][0],
            srcset=", ".join(f"{url} {w}w" for url, w in urls),
            width=sizes[-1],
            height=int(info["height"]),  # type: ignore[call-overload]
            backdrop=str(info["backdrop"]),
        )


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info


def _crop(image: Image.Image, ratio: float, focus: tuple[float, float]) -> Image.Image:
    """The largest ``ratio`` window of ``image``, centred on ``focus`` as far as the edges allow."""
    if image.width / image.height > ratio:
        width, height = round(image.height * ratio), image.height
    else:
        width, height = image.width, round(image.width / ratio)
    left = min(max(round(focus[0] * image.width - width / 2), 0), image.width - width)
    top = min(max(round(focus[1] * image.height - height / 2), 0), image.height - height)
    return image.crop((left, top, left + width, top + height))


def _backdrop(image: Image.Image) -> str:
    """Mean colour of the outer band of the photo, as a CSS hex colour."""
    rgb = image.convert("RGB")
    small = rgb.resize((100, max(1, round(100 * rgb.height / rgb.width))))
    band = max(1, round(BACKDROP_BAND * 100))
    totals = [0, 0, 0]
    count = 0
    for y in range(small.height):
        for x in range(small.width):
            if x < band or y < band or x >= small.width - band or y >= small.height - band:
                pixel: tuple[int, int, int] = small.getpixel((x, y))  # type: ignore[assignment]
                for i in range(3):
                    totals[i] += pixel[i]
                count += 1
    channels = [round(t / count) for t in totals]
    return "#{:02x}{:02x}{:02x}".format(*channels)
