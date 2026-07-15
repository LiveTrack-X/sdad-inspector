from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def native_executable(dist_root: Path) -> Path:
    candidates: list[Path]
    if sys.platform == "win32":
        candidates = [
            dist_root / "SDAD-Inspector.exe",
            dist_root / "SDAD-Inspector" / "SDAD-Inspector.exe",
        ]
    elif sys.platform == "darwin":
        candidates = [
            dist_root / "SDAD-Inspector",
            dist_root
            / "SDAD Inspector.app"
            / "Contents"
            / "MacOS"
            / "SDAD-Inspector",
            dist_root / "SDAD-Inspector" / "SDAD-Inspector",
        ]
    else:
        candidates = [
            dist_root / "SDAD-Inspector",
            dist_root / "SDAD-Inspector" / "SDAD-Inspector",
        ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No native executable was found in: " + ", ".join(map(str, candidates))
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded native launch smoke.")
    parser.add_argument("project_root", nargs="?", default=str(ROOT))
    parser.add_argument("--dist-root", default="build/native/dist")
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=45.0)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    executable = native_executable((ROOT / arguments.dist_root).resolve(strict=True))
    project = Path(arguments.project_root).resolve(strict=True)
    argv = [
        str(executable),
        str(project),
        "--hidden",
        "--smoke-seconds",
        str(arguments.seconds),
    ]
    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            shell=False,
            check=False,
            timeout=arguments.timeout,
        )
        exit_code = result.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        exit_code = 124
        timed_out = True
    payload = {
        "artifact": str(executable),
        "project": str(project),
        "exit_code": exit_code,
        "bounded_seconds": arguments.seconds,
        "timed_out": timed_out,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if exit_code == 0 else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
