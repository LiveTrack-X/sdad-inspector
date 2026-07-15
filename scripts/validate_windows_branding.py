from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION_INFO = {
    b"FileDescription": b"SDAD Inspector",
    b"ProductName": b"SDAD Inspector",
    b"FileVersion": b"0.0.2.0",
    b"ProductVersion": b"0.0.2",
    b"OriginalFilename": b"SDAD-Inspector.exe",
}


def _icon_frames(path: Path) -> Counter[tuple[int, str]]:
    payload = path.read_bytes()
    if len(payload) < 6 or payload[:4] != b"\x00\x00\x01\x00":
        raise ValueError(f"Invalid Windows icon header: {path}")
    count = struct.unpack_from("<H", payload, 4)[0]
    if count < 1 or len(payload) < 6 + count * 16:
        raise ValueError(f"Invalid Windows icon directory: {path}")
    frames: Counter[tuple[int, str]] = Counter()
    for index in range(count):
        entry = 6 + index * 16
        size, offset = struct.unpack_from("<II", payload, entry + 8)
        end = offset + size
        if not size or offset < 6 + count * 16 or end > len(payload):
            raise ValueError(f"Invalid Windows icon frame {index}: {path}")
        frame = payload[offset:end]
        frames[(len(frame), hashlib.sha256(frame).hexdigest())] += 1
    return frames


def _pe_icon_frames(pe: object, pefile: object) -> Counter[tuple[int, str]]:
    frames: Counter[tuple[int, str]] = Counter()
    resources = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    if resources is None:
        return frames
    icon_type = pefile.RESOURCE_TYPE["RT_ICON"]
    for entry in resources.entries:
        if entry.id != icon_type:
            continue
        for icon in entry.directory.entries:
            for language in icon.directory.entries:
                resource = language.data.struct
                frame = pe.get_data(resource.OffsetToData, resource.Size)
                frames[(len(frame), hashlib.sha256(frame).hexdigest())] += 1
    return frames


def _version_strings(pe: object) -> dict[bytes, bytes]:
    values: dict[bytes, bytes] = {}
    for group in getattr(pe, "FileInfo", []):
        for item in group:
            if item.Key == b"StringFileInfo":
                for table in item.StringTable:
                    values.update(table.entries)
    return values


def validate(executable: Path, source_icon: Path) -> dict[str, object]:
    if sys.platform != "win32":
        raise RuntimeError("Windows executable branding validation must run on Windows.")
    try:
        import pefile
    except ImportError as exc:  # pragma: no cover - build dependency contract
        raise RuntimeError("The Windows build environment is missing pefile.") from exc

    executable = executable.resolve(strict=True)
    source_icon = source_icon.resolve(strict=True)
    pe = pefile.PE(str(executable), fast_load=False)
    try:
        actual_version = _version_strings(pe)
        mismatches = {
            key.decode(): {
                "expected": expected.decode(),
                "actual": actual_version.get(key, b"").decode(errors="replace"),
            }
            for key, expected in EXPECTED_VERSION_INFO.items()
            if actual_version.get(key) != expected
        }
        if mismatches:
            raise ValueError(f"Unexpected Windows version metadata: {mismatches}")
        expected_frames = _icon_frames(source_icon)
        embedded_frames = _pe_icon_frames(pe, pefile)
        if embedded_frames != expected_frames:
            raise ValueError(
                "The executable RT_ICON resources do not exactly match "
                "packaging/sdad-inspector.ico."
            )
        return {
            "executable": str(executable),
            "product": actual_version[b"ProductName"].decode(),
            "product_version": actual_version[b"ProductVersion"].decode(),
            "file_version": actual_version[b"FileVersion"].decode(),
            "original_filename": actual_version[b"OriginalFilename"].decode(),
            "icon_frames": sum(embedded_frames.values()),
            "icon": "matches-source",
        }
    finally:
        pe.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Windows SDAD Inspector version and icon resources."
    )
    parser.add_argument(
        "--executable", default="build/native/dist/SDAD-Inspector.exe"
    )
    parser.add_argument("--source-icon", default="packaging/sdad-inspector.ico")
    arguments = parser.parse_args()
    evidence = validate(ROOT / arguments.executable, ROOT / arguments.source_icon)
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
