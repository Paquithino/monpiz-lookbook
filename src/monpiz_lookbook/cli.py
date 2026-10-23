"""Command line interface: ``build``, ``watch`` and ``check``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .builder import BuildOptions, build
from .content import load_lookbook
from .errors import LookbookError
from .pages.section import models_label
from .watch import watch

DEFAULT_CONTENT = Path("content/lookbook.yaml")
DEFAULT_ASSETS = Path("assets")
DEFAULT_OUTPUT = Path("dist/MonPiz-Lookbook.pdf")
PRINT_DPI = 300
PREVIEW_DPI = 150
EXIT_ERROR = 1


def _add_content_args(command: argparse.ArgumentParser) -> None:
    command.add_argument("--content", type=Path, default=DEFAULT_CONTENT, help="file YAML dei contenuti")
    command.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="cartella di font e immagini")


def _add_output_args(command: argparse.ArgumentParser, default_dpi: int) -> None:
    command.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="percorso del PDF")
    command.add_argument(
        "--dpi",
        type=int,
        default=default_dpi,
        help=f"risoluzione delle immagini (default {default_dpi}): 300 per la stampa, 150 per email",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="monpiz-lookbook", description="Genera il lookbook MonPiz in PDF.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    build_cmd = commands.add_parser("build", help="genera il PDF")
    _add_content_args(build_cmd)
    _add_output_args(build_cmd, PRINT_DPI)

    watch_cmd = commands.add_parser("watch", help="rigenera il PDF a ogni modifica salvata")
    _add_content_args(watch_cmd)
    _add_output_args(watch_cmd, PREVIEW_DPI)

    check_cmd = commands.add_parser("check", help="valida contenuti e asset senza generare il PDF")
    _add_content_args(check_cmd)
    return parser


def _options(args: argparse.Namespace) -> BuildOptions:
    return BuildOptions(args.content, args.assets, args.output, args.dpi)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            lookbook = load_lookbook(args.content, args.assets)
            summary = ", ".join(f"{s.name} ({models_label(len(s.models))})" for s in lookbook.sections)
            print(f"Contenuti validi: {summary}.")
        elif args.command == "watch":
            watch(_options(args))
        else:
            result = build(_options(args))
            size_mb = result.size_bytes / 1_000_000
            print(f"Creato {result.output} ({result.pages} pagine, {size_mb:.1f} MB)")
    except LookbookError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("\nInterrotto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
