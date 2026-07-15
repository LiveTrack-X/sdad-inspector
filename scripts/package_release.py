from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import stat
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+-alpha\.\d+$")
PLATFORMS = {"linux", "macos", "windows"}


def normalized_architecture(value: str) -> str:
    normalized = value.strip().casefold().replace("_", "-")
    aliases = {
        "amd64": "x64",
        "x86-64": "x64",
        "x64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported release architecture: {value}")
    return aliases[normalized]


def executable_name(platform_name: str) -> str:
    return "SDAD-Inspector.exe" if platform_name == "windows" else "SDAD-Inspector"


def release_source(dist_root: Path, platform_name: str) -> Path:
    source = dist_root / executable_name(platform_name)
    if not source.is_file():
        raise FileNotFoundError(f"Native single-file executable not found: {source}")
    if source.is_symlink():
        raise ValueError(f"Native release executable must not be a symbolic link: {source}")
    return source


def _write_zip(source: Path, destination: Path) -> None:
    info = zipfile.ZipInfo(source.name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o755) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        archive.writestr(info, source.read_bytes())


def _write_tar_gz(source: Path, destination: Path) -> None:
    with destination.open("wb") as raw_file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                info = tarfile.TarInfo(source.name)
                info.size = source.stat().st_size
                info.mode = 0o755
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0
                with source.open("rb") as source_file:
                    archive.addfile(info, source_file)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_archive(
    *,
    dist_root: Path,
    output_dir: Path,
    platform_name: str,
    version: str,
    architecture: str,
) -> dict[str, object]:
    platform_name = platform_name.casefold()
    if platform_name not in PLATFORMS:
        raise ValueError(f"Unsupported release platform: {platform_name}")
    if not RELEASE_VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"Release version must use X.Y.Z-alpha.N: {version}")
    architecture = normalized_architecture(architecture)
    source = release_source(dist_root.resolve(strict=True), platform_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".zip" if platform_name == "windows" else ".tar.gz"
    destination = output_dir / (
        f"SDAD-Inspector-{version}-{platform_name}-{architecture}{suffix}"
    )
    if platform_name == "windows":
        _write_zip(source, destination)
    else:
        _write_tar_gz(source, destination)
    return {
        "archive": str(destination.resolve()),
        "archive_member": source.name,
        "archive_member_count": 1,
        "bytes": destination.stat().st_size,
        "package_mode": "unsigned-one-file-portable",
        "platform": platform_name,
        "architecture": architecture,
        "sha256": _sha256(destination),
        "unsigned": True,
        "version": version,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive one unsigned portable SDAD Inspector executable."
    )
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS))
    parser.add_argument("--arch", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist-root", default="build/native/dist")
    parser.add_argument("--output-dir", default="release-artifacts")
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    evidence = build_release_archive(
        dist_root=ROOT / arguments.dist_root,
        output_dir=ROOT / arguments.output_dir,
        platform_name=arguments.platform,
        version=arguments.version,
        architecture=arguments.arch,
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
