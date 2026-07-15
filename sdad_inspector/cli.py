from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__
from .errors import InspectorError
from .report import generate_static_report
from .server import serve_browser
from .snapshot import inspect_project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdad-inspector",
        description="Inspect an SDAD repository without changing it.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    inspect = subcommands.add_parser("inspect", help="emit normalized snapshot JSON")
    inspect.add_argument("project_root", help="SDAD project root to inspect")
    inspect.add_argument(
        "--sdad-checkout", required=True, help="clean released SDAD checkout or release archive"
    )
    inspect.add_argument("--timeout", type=float, default=30.0)
    inspect.add_argument("--no-strict", action="store_true")
    inspect.add_argument("--pretty", action="store_true")
    serve = subcommands.add_parser("serve", help="run the loopback browser application")
    serve.add_argument("project_root", help="SDAD project root to inspect")
    serve.add_argument(
        "--sdad-checkout", required=True, help="clean released SDAD checkout or release archive"
    )
    serve.add_argument("--web-root", default="web/dist", help="built frontend directory")
    serve.add_argument("--port", type=int, default=0, help="loopback port; 0 chooses a free port")
    serve.add_argument("--no-browser", action="store_true")
    report = subcommands.add_parser("report", help="write an offline sanitized HTML report")
    report.add_argument("project_root", help="SDAD project root to inspect")
    report.add_argument(
        "--sdad-checkout", required=True, help="clean released SDAD checkout or release archive"
    )
    report.add_argument("--output", required=True, help="HTML output outside the inspected project")
    report.add_argument("--redact-paths", action="store_true")
    report.add_argument("--redact-evidence", action="store_true")
    report.add_argument("--overwrite", action="store_true")
    desktop = subcommands.add_parser("desktop", help="run the optional native preview")
    desktop.add_argument("project_root", help="SDAD project root to inspect")
    desktop.add_argument(
        "--sdad-checkout",
        help="clean released SDAD checkout; required in source mode",
    )
    desktop.add_argument("--web-root", help="built frontend directory")
    desktop.add_argument("--hidden", action="store_true", help=argparse.SUPPRESS)
    desktop.add_argument("--smoke-seconds", type=float, help=argparse.SUPPRESS)
    desktop.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "inspect":
            payload = inspect_project(
                arguments.project_root,
                arguments.sdad_checkout,
                timeout=arguments.timeout,
                strict=not arguments.no_strict,
            )
        elif arguments.command == "serve":
            return serve_browser(
                arguments.project_root,
                arguments.sdad_checkout,
                arguments.web_root,
                port=arguments.port,
                open_browser=not arguments.no_browser,
            )
        elif arguments.command == "report":
            payload = generate_static_report(
                arguments.project_root,
                arguments.sdad_checkout,
                arguments.output,
                redact_paths=arguments.redact_paths,
                redact_evidence=arguments.redact_evidence,
                overwrite=arguments.overwrite,
            )
        elif arguments.command == "desktop":
            from .desktop import run_desktop

            return run_desktop(
                arguments.project_root,
                arguments.sdad_checkout,
                arguments.web_root,
                hidden=arguments.hidden,
                smoke_seconds=arguments.smoke_seconds,
                port=arguments.port,
            )
        else:  # pragma: no cover - argparse enforces the command set.
            raise AssertionError(arguments.command)
    except InspectorError as exc:
        json.dump(exc.to_payload(), sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        return 2
    json.dump(
        payload,
        sys.stdout,
        ensure_ascii=False,
        indent=2 if arguments.pretty else None,
        sort_keys=False,
    )
    sys.stdout.write("\n")
    return 0
