"""Derive release identities without importing optional application dependencies."""
from __future__ import annotations

import argparse
import os
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT / "sdad_inspector/version.py"))["__version__"]
if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", VERSION):
    raise ValueError("A regular release requires a canonical major.minor.patch version")
TAG = "v" + VERSION
WINDOWS_VERSION = tuple(map(int, VERSION.split("."))) + (0,)
WINDOWS_VERSION_STRING = VERSION + ".0"
GUIDES = ("README.md", "README.ko.md", "README.ja.md", "README.zh-CN.md")
SOURCE_START = "<!-- inspector-source-version -->"
SOURCE_END = "<!-- /inspector-source-version -->"


def source_version_block() -> str:
    return f"{SOURCE_START}Source version: `{TAG}`{SOURCE_END}"


def managed_source_guide(text: str) -> str:
    """Replace only one explicit source identity; published facts are authored."""
    if text.count(SOURCE_START) != 1 or text.count(SOURCE_END) != 1:
        raise ValueError("exactly one managed source-version block is required")
    start, end = text.index(SOURCE_START), text.index(SOURCE_END)
    if end < start or "\n" in text[start:end] or "\r" in text[start:end]:
        raise ValueError("managed source-version block must occupy one line")
    return text[:start] + source_version_block() + text[end + len(SOURCE_END):]


def windows_resource() -> str:
    template = (ROOT / "packaging/sdad-inspector-version.txt.in").read_text(encoding="utf-8")
    return (template.replace("@NUMERIC_VERSION@", str(WINDOWS_VERSION))
            .replace("@FILE_VERSION@", WINDOWS_VERSION_STRING)
            .replace("@PRODUCT_VERSION@", VERSION))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--github-output", action="store_true")
    args = parser.parse_args()
    resource = ROOT / "packaging/sdad-inspector-version.txt"
    expected = windows_resource()
    guides = []
    if args.sync or args.check:
        # Validate all inputs before writing. Each guide derives directly from
        # VERSION, so a partial write can be retried independently of the resource.
        for name in GUIDES:
            path = ROOT / name
            text = path.read_bytes().decode("utf-8")
            try:
                updated = managed_source_guide(text)
            except ValueError as exc:
                raise SystemExit(f"{name}: {exc}") from exc
            guides.append((path, text, updated))
    if args.sync:
        for path, text, updated in guides:
            if text != updated:
                path.write_bytes(updated.encode("utf-8"))
        resource.write_text(expected, encoding="utf-8", newline="\n")
    if args.check:
        if any(path.read_bytes().decode("utf-8") != updated for path, _, updated in guides):
            raise SystemExit("README source version is stale; run python scripts/release_metadata.py --sync")
        if resource.read_text(encoding="utf-8") != expected:
            raise SystemExit("Windows resource is stale; run python scripts/release_metadata.py --sync")
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"version={VERSION}\ntag={TAG}\nnotes=docs/releases/{TAG}.md\n")
    elif not args.check and not args.sync:
        print(VERSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
