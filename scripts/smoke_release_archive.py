from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def current_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def expected_executable_name(platform_name: str) -> str:
    return "SDAD-Inspector.exe" if platform_name == "windows" else "SDAD-Inspector"


def find_release_archive(root: Path, platform_name: str) -> Path:
    candidates = sorted(
        [
            *root.glob(f"SDAD-Inspector-*-{platform_name}-*.zip"),
            *root.glob(f"SDAD-Inspector-*-{platform_name}-*.tar.gz"),
        ],
        key=lambda path: path.name,
    )
    if len(candidates) != 1:
        raise ValueError(
            f"Expected one {platform_name} release archive, found {len(candidates)}"
        )
    return candidates[0]


def _safe_member_name(name: str, expected: str) -> None:
    normalized = name.replace("\\", "/")
    if normalized != expected or "/" in normalized:
        raise ValueError(
            f"Release archive must contain only root executable {expected!r}: {name!r}"
        )


def extract_single_executable(
    archive: Path, destination: Path, platform_name: str
) -> Path:
    expected = expected_executable_name(platform_name)
    destination.mkdir(parents=True, exist_ok=False)
    target = destination / expected
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as packaged:
            members = packaged.infolist()
            if len(members) != 1 or members[0].is_dir():
                raise ValueError(
                    f"Release archive must contain exactly one file; found {len(members)}"
                )
            member = members[0]
            _safe_member_name(member.filename, expected)
            mode = (member.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError("Release executable must not be a symbolic link")
            with packaged.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    elif archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as packaged:
            members = packaged.getmembers()
            if len(members) != 1 or not members[0].isfile():
                raise ValueError(
                    f"Release archive must contain exactly one regular file; found {len(members)}"
                )
            member = members[0]
            _safe_member_name(member.name, expected)
            source = packaged.extractfile(member)
            if source is None:
                raise ValueError("Release executable could not be read")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    else:
        raise ValueError(f"Unsupported release archive: {archive.name}")
    if platform_name != "windows":
        target.chmod(0o755)
    return target


def smoke_archive(
    archive: Path,
    project_root: Path,
    *,
    seconds: float = 2.0,
    timeout: float = 60.0,
) -> dict[str, object]:
    platform_name = current_platform()
    if f"-{platform_name}-" not in archive.name:
        raise ValueError(
            f"Archive {archive.name!r} does not target runner platform {platform_name!r}"
        )
    with tempfile.TemporaryDirectory(prefix="sdad-inspector-portable-smoke-") as raw:
        temporary = Path(raw)
        executable = extract_single_executable(
            archive.resolve(strict=True), temporary / "extracted", platform_name
        )
        environment = os.environ.copy()
        environment.pop("PYTHONHOME", None)
        environment.pop("PYTHONPATH", None)
        argv = [
            str(executable),
            str(project_root.resolve(strict=True)),
            "--hidden",
            "--smoke-seconds",
            str(seconds),
        ]
        try:
            result = subprocess.run(
                argv,
                cwd=temporary,
                env=environment,
                shell=False,
                check=False,
                timeout=timeout,
            )
            exit_code = result.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            exit_code = 124
            timed_out = True
        extracted_entries = sorted(
            path.relative_to(temporary / "extracted").as_posix()
            for path in (temporary / "extracted").rglob("*")
        )
        payload = {
            "archive": archive.name,
            "archive_member_count": 1,
            "extracted_entries": extracted_entries,
            "platform": platform_name,
            "project": str(project_root.resolve(strict=True)),
            "exit_code": exit_code,
            "bounded_seconds": seconds,
            "timed_out": timed_out,
            "python_runtime_installed_for_product": False,
        }
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract and smoke one downloaded portable release archive."
    )
    parser.add_argument("project_root", nargs="?", default=str(ROOT))
    parser.add_argument("--artifact-dir", default="release-candidate")
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    platform_name = current_platform()
    archive = find_release_archive(
        (ROOT / arguments.artifact_dir).resolve(strict=True), platform_name
    )
    payload = smoke_archive(
        archive,
        Path(arguments.project_root),
        seconds=arguments.seconds,
        timeout=arguments.timeout,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["exit_code"] == 0 else int(payload["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
