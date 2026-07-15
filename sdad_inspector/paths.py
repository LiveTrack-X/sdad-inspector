from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable

from .errors import BoundedReadError, PathSafetyError

MAX_CONTROL_BYTES = 64 * 1024
MAX_CONTROL_LINES = 500

_SENSITIVE_NAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "cookies",
    "cookies.json",
    "id_rsa",
    "id_ed25519",
}
_SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


def canonical_directory(value: str | os.PathLike[str], *, label: str) -> Path:
    raw = Path(value).expanduser()
    try:
        resolved = raw.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathSafetyError(
            f"{label} is not a readable directory.", details={"path": str(raw)}
        ) from exc
    if not resolved.is_dir():
        raise PathSafetyError(
            f"{label} is not a directory.", details={"path": str(resolved)}
        )
    return resolved


def _is_sensitive(part: str) -> bool:
    lowered = part.casefold()
    return lowered in _SENSITIVE_NAMES or Path(lowered).suffix in _SENSITIVE_SUFFIXES


def safe_project_path(
    root: Path,
    relative: str,
    *,
    purpose: str,
    must_exist: bool = False,
    regular_file: bool = True,
) -> Path:
    if not isinstance(relative, str) or not relative.strip() or "\x00" in relative:
        raise PathSafetyError(f"{purpose} is not a valid repository path.")
    supplied = Path(relative)
    if supplied.is_absolute() or supplied.drive:
        raise PathSafetyError(
            f"{purpose} must be repository-relative.", details={"path": relative}
        )
    if any(part in {"", ".", ".."} for part in supplied.parts):
        raise PathSafetyError(
            f"{purpose} contains an unsafe path segment.", details={"path": relative}
        )
    if any(_is_sensitive(part) for part in supplied.parts):
        raise PathSafetyError(
            f"{purpose} points to a sensitive file class.", details={"path": relative}
        )

    canonical_root = canonical_directory(root, label="Selected project")
    candidate = canonical_root.joinpath(*supplied.parts)
    cursor = canonical_root
    for part in supplied.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise PathSafetyError(
                f"{purpose} traverses a symbolic link.", details={"path": relative}
            )

    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(canonical_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PathSafetyError(
            f"{purpose} escapes the selected project.", details={"path": relative}
        ) from exc

    if must_exist:
        if regular_file and not resolved.is_file():
            raise PathSafetyError(
                f"{purpose} is not a regular file.", details={"path": relative}
            )
        if regular_file and resolved.stat().st_nlink > 1:
            raise PathSafetyError(
                f"{purpose} is a hard-linked file.", details={"path": relative}
            )
    return resolved


def read_bounded_text(
    root: Path,
    relative: str,
    *,
    purpose: str,
    required: bool = False,
    max_bytes: int = MAX_CONTROL_BYTES,
    max_lines: int = MAX_CONTROL_LINES,
) -> str | None:
    candidate = safe_project_path(
        root, relative, purpose=purpose, must_exist=False, regular_file=True
    )
    if not candidate.exists():
        if required:
            raise BoundedReadError(
                f"{purpose} does not exist.", details={"path": relative}
            )
        return None
    candidate = safe_project_path(
        root, relative, purpose=purpose, must_exist=True, regular_file=True
    )
    try:
        data = candidate.read_bytes()
    except OSError as exc:
        raise BoundedReadError(
            f"{purpose} could not be read.", details={"path": relative}
        ) from exc
    if len(data) > max_bytes:
        raise BoundedReadError(
            f"{purpose} exceeds the {max_bytes}-byte inspection budget.",
            details={"path": relative, "bytes": len(data)},
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BoundedReadError(
            f"{purpose} is not valid UTF-8.", details={"path": relative}
        ) from exc
    line_count = len(text.splitlines())
    if line_count > max_lines:
        raise BoundedReadError(
            f"{purpose} exceeds the {max_lines}-line inspection budget.",
            details={"path": relative, "lines": line_count},
        )
    return text


def file_metadata(root: Path, relative: str) -> dict[str, object]:
    candidate = safe_project_path(
        root, relative, purpose="control evidence", must_exist=False
    )
    if not candidate.exists():
        return {"path": relative, "exists": False}
    candidate = safe_project_path(
        root, relative, purpose="control evidence", must_exist=True
    )
    stat = candidate.stat()
    return {
        "path": relative,
        "exists": True,
        "bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }


def control_fingerprint(root: Path, paths: Iterable[str]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for relative in sorted(set(paths)):
        try:
            result[relative] = file_metadata(root, relative)
        except PathSafetyError as exc:
            result[relative] = {
                "path": relative,
                "exists": False,
                "unsafe": True,
                "reason": exc.message,
            }
    return result
