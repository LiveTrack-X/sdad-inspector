#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdad_inspector.report import generate_static_report  # noqa: E402

EXCLUDED_PARTS = {
    ".git",
    ".runtime",
    ".npm-cache",
    "node_modules",
    "dist",
    "__pycache__",
}


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.attributes: set[str] = set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.casefold())
        self.attributes.update(name.casefold() for name, _ in attrs)


def fingerprint() -> dict[str, tuple[int, int, str]]:
    result: dict[str, tuple[int, int, str]] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        stat = path.stat()
        result[relative.as_posix()] = (
            stat.st_size,
            stat.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the static report contract.")
    parser.add_argument(
        "--sdad-checkout",
        type=Path,
        default=ROOT / ".runtime" / "sdad-v3.2.2",
        help="Path to a clean authenticated SDAD v3.2.2 checkout.",
    )
    args = parser.parse_args(argv)
    engine = args.sdad_checkout.resolve()
    require(engine.is_dir(), "Clean v3.2.2 runtime archive is missing.")
    before = fingerprint()
    with tempfile.TemporaryDirectory(prefix="sdad-inspector-report-") as directory:
        output = Path(directory) / "inspection.html"
        result = generate_static_report(
            ROOT,
            engine,
            output,
            redact_paths=True,
            redact_evidence=True,
        )
        document = output.read_text(encoding="utf-8")
        parser = SurfaceParser()
        parser.feed(document)
        require(result["bytes"] == len(document.encode("utf-8")), "Report byte count drifted.")
        require(ROOT.as_posix() not in document, "Forward-slash project path leaked.")
        require(str(ROOT) not in document, "Project path leaked.")
        require(str(engine) not in document, "Engine path leaked.")
        require("&lt;PROJECT_ROOT&gt;" in document, "Path redaction marker is missing.")
        require("evidence_redacted" in document, "Evidence redaction marker is missing.")
        require(
            not ({"script", "link", "iframe", "object", "embed"} & parser.tags),
            "Report contains an active or external-resource element.",
        )
        require("src" not in parser.attributes and "href" not in parser.attributes, "Report can fetch a resource.")
        require("Content-Security-Policy" in document, "Report CSP is missing.")
    after = fingerprint()
    require(before == after, "Static report validation modified the inspected project.")
    print(
        "Static report OK: escaped offline HTML, paths/evidence redacted, "
        "outside-project atomic output, project writes 0."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
