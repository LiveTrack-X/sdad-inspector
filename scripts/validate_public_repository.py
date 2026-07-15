from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


MAX_PUBLIC_FILE_BYTES = 50 * 1024 * 1024
MAX_TEXT_SCAN_BYTES = 2 * 1024 * 1024
GENERATED_PARTS = {
    ".npm-cache",
    ".runtime",
    ".venv",
    ".agents",
    ".codex",
    ".idea",
    ".vscode",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "release-artifacts",
}
SENSITIVE_NAMES = {
    ".env",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
}
LOCAL_ONLY_NAMES = {".coverage", ".ds_store", "desktop.ini", "thumbs.db"}
LOCAL_ONLY_PATHS = {PurePosixPath("design-qa.md")}
SENSITIVE_SUFFIXES = {
    ".jks",
    ".kdbx",
    ".key",
    ".p12",
    ".pem",
    ".pfx",
}
TEXT_PATTERNS = {
    "personal absolute path": re.compile(
        r"(?i)(?:[A-Z]:[\\/](?:Users)[\\/][^\\/\s`\"']+|/(?:Users|home)/[^/\s`\"']+)"
    ),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
}
PERSONAL_PATH_FIXTURE_FILES = {
    PurePosixPath("tests/test_preferences.py"),
}


def repository_paths(root: Path) -> list[PurePosixPath]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [
        PurePosixPath(raw.decode("utf-8"))
        for raw in completed.stdout.split(b"\0")
        if raw
    ]


def audit_bytes(path: PurePosixPath, data: bytes) -> list[str]:
    issues: list[str] = []
    lowered_parts = [part.lower() for part in path.parts]
    name = path.name.lower()

    if any(part in GENERATED_PARTS for part in lowered_parts):
        issues.append(f"{path}: generated or local-only directory is included")
    if tuple(lowered_parts[:2]) == ("design", "qa"):
        issues.append(f"{path}: historical QA capture is included")
    if path in LOCAL_ONLY_PATHS:
        issues.append(f"{path}: historical local QA ledger is included")
    if name in LOCAL_ONLY_NAMES:
        issues.append(f"{path}: local-only file is included")
    if name in SENSITIVE_NAMES or name.startswith(".env.") or path.suffix.lower() in SENSITIVE_SUFFIXES:
        issues.append(f"{path}: sensitive filename is included")
    if len(data) > MAX_PUBLIC_FILE_BYTES:
        issues.append(f"{path}: file exceeds the 50 MiB public-source limit")

    if len(data) > MAX_TEXT_SCAN_BYTES or b"\0" in data:
        return issues
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return issues

    for label, pattern in TEXT_PATTERNS.items():
        if label == "personal absolute path" and path in PERSONAL_PATH_FIXTURE_FILES:
            continue
        if pattern.search(text):
            issues.append(f"{path}: contains a {label}")
    return issues


def audit_repository(root: Path) -> tuple[list[str], int]:
    issues: list[str] = []
    paths = repository_paths(root)
    for relative_path in paths:
        full_path = root.joinpath(*relative_path.parts)
        issues.extend(audit_bytes(relative_path, full_path.read_bytes()))
    return issues, len(paths)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    issues, count = audit_repository(root)
    if issues:
        print("Public repository validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(f"Public repository validation passed: {count} files checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
