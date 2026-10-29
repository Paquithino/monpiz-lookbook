"""Generate the static font instances used by the lookbook.

ReportLab can only embed static TrueType fonts, while Fraunces and Inter are
distributed by Google Fonts as variable fonts. This script pins the variable
axes to the values used in the design and writes static TTFs to
``assets/fonts``. It is a one-off maintenance tool, not part of the build.

Usage:
    python scripts/instance_fonts.py \
        --fraunces "path/to/Fraunces[SOFT,WONK,opsz,wght].ttf" \
        --fraunces-italic "path/to/Fraunces-Italic[SOFT,WONK,opsz,wght].ttf" \
        --inter "path/to/Inter[opsz,wght].ttf"

Sources: https://github.com/google/fonts (ofl/fraunces, ofl/inter).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

# (source key, output file, axis location)
INSTANCES: tuple[tuple[str, str, dict[str, float]], ...] = (
    ("fraunces", "Fraunces-Display.ttf", {"opsz": 48, "wght": 500, "SOFT": 0, "WONK": 0}),
    ("fraunces", "Fraunces-Text.ttf", {"opsz": 14, "wght": 500, "SOFT": 0, "WONK": 0}),
    ("fraunces_italic", "Fraunces-DisplayItalic.ttf", {"opsz": 48, "wght": 500, "SOFT": 0, "WONK": 0}),
    ("inter", "Inter-Regular.ttf", {"opsz": 14, "wght": 400}),
)


def build_instance(source: Path, target: Path, location: dict[str, float]) -> None:
    instance = instantiateVariableFont(TTFont(source), location)
    # The STAT table has no entries for arbitrary axis values, so fontTools
    # cannot derive names automatically: name the instance after its file.
    name = target.stem
    family, _, style = name.partition("-")
    names = instance["name"]
    names.setName(family, 1, 3, 1, 0x409)
    names.setName(style or "Regular", 2, 3, 1, 0x409)
    names.setName(f"{family} {style}".strip(), 4, 3, 1, 0x409)
    names.setName(name, 6, 3, 1, 0x409)
    instance.save(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fraunces", type=Path, required=True)
    parser.add_argument("--fraunces-italic", type=Path, required=True)
    parser.add_argument("--inter", type=Path, required=True)
    args = parser.parse_args()

    sources = {"fraunces": args.fraunces, "fraunces_italic": args.fraunces_italic, "inter": args.inter}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, filename, location in INSTANCES:
        target = OUTPUT_DIR / filename
        build_instance(sources[key], target, location)
        print(f"{target.relative_to(OUTPUT_DIR.parents[1])}  {location}")


if __name__ == "__main__":
    main()
