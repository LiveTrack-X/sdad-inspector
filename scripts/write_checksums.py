from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def archive_files(root: Path) -> list[Path]:
    return sorted(
        [*root.glob("SDAD-Inspector-*.zip"), *root.glob("SDAD-Inspector-*.tar.gz")],
        key=lambda path: path.name,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(root: Path, *, expected: int = 3) -> dict[str, object]:
    archives = archive_files(root)
    if len(archives) != expected:
        raise ValueError(f"Expected {expected} release archives, found {len(archives)}")
    platforms = {name for name in ("windows", "macos", "linux") if any(f"-{name}-" in path.name for path in archives)}
    if platforms != {"windows", "macos", "linux"}:
        raise ValueError(f"Release archives do not cover all platforms: {sorted(platforms)}")
    checksums = root / "SHA256SUMS"
    lines = [f"{sha256(path)}  {path.name}" for path in archives]
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return {
        "archives": [path.name for path in archives],
        "checksums": str(checksums.resolve()),
        "count": len(archives),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write SHA256SUMS for release archives.")
    parser.add_argument("root", nargs="?", default="release-artifacts")
    parser.add_argument("--expected", type=int, default=3)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    evidence = write_checksums(Path(arguments.root).resolve(strict=True), expected=arguments.expected)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
