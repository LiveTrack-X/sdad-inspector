from __future__ import annotations

import argparse
import json
import runpy
import sys
from collections.abc import Sequence
from pathlib import Path

from sdad_inspector.desktop import resource_root, run_desktop
from sdad_inspector.dialogs import select_project_directory
from sdad_inspector.engine import authenticate_release_archive
from sdad_inspector.errors import InspectorError
from sdad_inspector.updater import (
    INTERNAL_UPDATE_FLAG,
    apply_update_plan,
    refresh_windows_icon_cache,
)

INTERNAL_ENGINE_FLAG = "--sdad-internal-engine"


def run_bundled_engine(arguments: Sequence[str]) -> int:
    engine_root = resource_root() / "sdad-engine"
    authenticate_release_archive(engine_root)
    script = engine_root / "scripts" / "sdad.py"
    previous_argv = sys.argv
    previous_bytecode = sys.dont_write_bytecode
    sys.argv = [str(script), *arguments]
    sys.dont_write_bytecode = True
    try:
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            return 1
        return 0
    finally:
        sys.argv = previous_argv
        sys.dont_write_bytecode = previous_bytecode


def show_native_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except (ImportError, OSError):
        return
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror("SDAD Inspector", message)
    finally:
        root.destroy()


def refresh_frozen_windows_icon() -> bool:
    """Refresh a manually replaced portable EXE without affecting startup."""

    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    try:
        return refresh_windows_icon_cache(Path(sys.executable))
    except Exception:
        return False


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open SDAD Inspector desktop preview.")
    parser.add_argument("project_root", nargs="?", help="SDAD project root")
    parser.add_argument("--sdad-checkout", help="explicit clean released SDAD checkout")
    parser.add_argument("--web-root", help="explicit built frontend directory")
    parser.add_argument("--hidden", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-seconds", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=0, help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    if raw_arguments[:1] == [INTERNAL_UPDATE_FLAG]:
        if len(raw_arguments) != 2:
            return 2
        return apply_update_plan(raw_arguments[1])
    if raw_arguments[:1] == [INTERNAL_ENGINE_FLAG]:
        try:
            return run_bundled_engine(raw_arguments[1:])
        except InspectorError as exc:
            json.dump(exc.to_payload(), sys.stderr, ensure_ascii=False)
            sys.stderr.write("\n")
            return 2
    refresh_frozen_windows_icon()
    arguments = _parser().parse_args(raw_arguments)
    project_root = arguments.project_root
    try:
        if project_root is None:
            project_root = select_project_directory()
            if project_root is None:
                return 0
        return run_desktop(
            Path(project_root),
            arguments.sdad_checkout,
            arguments.web_root,
            hidden=arguments.hidden,
            smoke_seconds=arguments.smoke_seconds,
            port=arguments.port,
        )
    except InspectorError as exc:
        json.dump(exc.to_payload(), sys.stderr, ensure_ascii=False, indent=2)
        sys.stderr.write("\n")
        if getattr(sys, "frozen", False) and not arguments.hidden:
            show_native_error(exc.message)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
