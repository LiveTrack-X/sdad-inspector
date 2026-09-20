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
    if args.sync:
        old = re.search(r"ProductVersion', '([^']+)'", resource.read_text(encoding="utf-8"))
        # Current download guides are derived; historical release notes are never rewritten.
        if old and old[1] != VERSION:
            for name in ("README.md", "README.ko.md", "README.ja.md", "README.zh-CN.md"):
                path = ROOT / name
                path.write_text(path.read_text(encoding="utf-8").replace(old[1], VERSION), encoding="utf-8", newline="\n")
        # Commit the derived resource last. A partial guide-write failure leaves
        # the old version discoverable, so the same --sync invocation can retry.
        resource.write_text(expected, encoding="utf-8", newline="\n")
    if args.check and resource.read_text(encoding="utf-8") != expected:
        raise SystemExit("Windows resource is stale; run python scripts/release_metadata.py --sync")
    if args.github_output:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"version={VERSION}\ntag={TAG}\nnotes=docs/releases/{TAG}.md\n")
    elif not args.check and not args.sync:
        print(VERSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
