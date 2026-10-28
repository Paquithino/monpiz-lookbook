"""Command line interface: ``build``, ``watch``, ``web`` and ``check``."""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .builder import BuildOptions, build
from .content import load_lookbook
from .errors import LookbookError
from .pages.section import models_label
from .watch import PACKAGE_DIR, run, site_command, watch
from .web import SiteOptions, build_site

DEFAULT_CONTENT = Path("content/lookbook.yaml")
DEFAULT_ASSETS = Path("assets")
DEFAULT_OUTPUT = Path("dist/MonPiz-Lookbook.pdf")
DEFAULT_SITE = Path("site")
DEFAULT_PORT = 8000
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
    build_cmd.add_argument(
        "--crop-marks", action="store_true", help="aggiunge i segni di taglio per la tipografia"
    )
    build_cmd.add_argument(
        "--no-bleed",
        action="store_true",
        help="senza abbondanza: per la versione online o da spedire via email",
    )

    watch_cmd = commands.add_parser("watch", help="rigenera il PDF a ogni modifica salvata")
    _add_content_args(watch_cmd)
    _add_output_args(watch_cmd, PREVIEW_DPI)

    web_cmd = commands.add_parser("web", help="genera la rivista digitale (sito statico)")
    _add_content_args(web_cmd)
    web_cmd.add_argument("-o", "--output", type=Path, default=DEFAULT_SITE, help="cartella del sito")
    web_cmd.add_argument(
        "--watch",
        action="store_true",
        help=f"anteprima su http://localhost:{DEFAULT_PORT}, rigenerata a ogni modifica",
    )

    check_cmd = commands.add_parser("check", help="valida contenuti e asset senza generare il PDF")
    _add_content_args(check_cmd)
    return parser


def _options(args: argparse.Namespace) -> BuildOptions:
    return BuildOptions(
        args.content,
        args.assets,
        args.output,
        args.dpi,
        # The live preview shows the trimmed page; a build is for print unless told otherwise.
        bleed=args.command == "build" and not args.no_bleed,
        crop_marks=getattr(args, "crop_marks", False),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            lookbook = load_lookbook(args.content, args.assets)
            summary = ", ".join(f"{s.name} ({models_label(len(s.models))})" for s in lookbook.sections)
            print(f"Contenuti validi: {summary}.")
        elif args.command == "watch":
            watch(_options(args))
        elif args.command == "web":
            if args.watch:
                _serve(args.output)
                roots = [args.content.parent, args.assets, PACKAGE_DIR]
                run(roots, site_command(args.content, args.assets, args.output))
            else:
                site = build_site(SiteOptions(args.content, args.assets, args.output))
                size_mb = site.size_bytes / 1_000_000
                summary = f"{site.images} immagini, {size_mb:.1f} MB in totale"
                print(f"Creato {site.output_dir}/index.html ({summary})")
        else:
            result = build(_options(args))
            size_mb = result.size_bytes / 1_000_000
            print(f"Creato {result.output} ({result.pages} pagine, {size_mb:.1f} MB)")
            if result.blank_pages_needed:
                print(
                    f"Nota: per la stampa a punto metallico le pagine devono essere un multiplo di 4: "
                    f"ne mancano {result.blank_pages_needed}."
                )
    except LookbookError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("\nInterrotto.")
    return 0


def _serve(folder: Path) -> None:
    """Serve ``folder`` on localhost in the background, for the live preview."""
    folder.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(_QuietHandler, directory=str(folder))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", DEFAULT_PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Anteprima su http://localhost:{DEFAULT_PORT}", flush=True)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    sys.exit(main())
