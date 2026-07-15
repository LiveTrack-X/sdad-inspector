from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path, PurePosixPath


MAX_PUBLIC_FILE_BYTES = 50 * 1024 * 1024
MAX_TEXT_SCAN_BYTES = 2 * 1024 * 1024
PUBLIC_IMAGE_MANIFEST = PurePosixPath("docs/assets/public-assets.json")
PUBLIC_IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
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
PRIVATE_CONTROL_FILES = {
    "sdad-state.yaml",
    "review-findings.md",
    "sdad_inspector_product_plan.md",
    "docs/design_reference.md",
    "docs/index.md",
    "docs/todo-open-items.md",
    "docs/claim-registry.md",
    "docs/evidence-matrix.md",
    "docs/implementation-notes.md",
    "docs/owner_decisions.md",
    "docs/repository-operating-rules.md",
    "docs/update_and_migration.md",
    "docs/artifact-contracts.md",
    "docs/readiness-assessment.md",
    "docs/remote-import-record.md",
    "docs/work-packet-state.md",
    "scripts/validate_packet_0.py",
    "tests/test_packet_0.py",
}
PRIVATE_CONTROL_PREFIXES = (
    "spec/",
    "design/reference/",
    "docs/sdad/",
    "docs/handoffs/",
)
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
    normalized_path = path.as_posix().lower()

    if (
        name == "agents.md"
        or normalized_path in PRIVATE_CONTROL_FILES
        or normalized_path.startswith(PRIVATE_CONTROL_PREFIXES)
    ):
        issues.append(f"{path}: private SDAD control-plane path is included")
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


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return (width, height) if width > 0 and height > 0 else None


def audit_public_images(files: dict[PurePosixPath, bytes]) -> list[str]:
    issues: list[str] = []
    images = {
        path: data
        for path, data in files.items()
        if path.suffix.lower() in PUBLIC_IMAGE_SUFFIXES
    }
    manifest_bytes = files.get(PUBLIC_IMAGE_MANIFEST)
    if manifest_bytes is None:
        return [f"{PUBLIC_IMAGE_MANIFEST}: public image integrity manifest is missing"]
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [f"{PUBLIC_IMAGE_MANIFEST}: public image integrity manifest is invalid"]
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("assets"), list):
        return [f"{PUBLIC_IMAGE_MANIFEST}: expected schema_version 1 and an assets list"]

    entries: dict[PurePosixPath, dict[str, object]] = {}
    for raw_entry in manifest["assets"]:
        if not isinstance(raw_entry, dict) or not isinstance(raw_entry.get("path"), str):
            issues.append(f"{PUBLIC_IMAGE_MANIFEST}: every asset needs a string path")
            continue
        path = PurePosixPath(raw_entry["path"])
        if path in entries:
            issues.append(f"{PUBLIC_IMAGE_MANIFEST}: duplicate asset {path}")
            continue
        entries[path] = raw_entry

    missing_entries = sorted(images.keys() - entries.keys())
    extra_entries = sorted(entries.keys() - images.keys())
    for path in missing_entries:
        issues.append(f"{path}: public image is not integrity-manifested")
    for path in extra_entries:
        issues.append(f"{path}: image manifest entry has no matching public image")

    for path in sorted(images.keys() & entries.keys()):
        data = images[path]
        entry = entries[path]
        digest = hashlib.sha256(data).hexdigest()
        if entry.get("sha256") != digest:
            issues.append(f"{path}: public image SHA-256 does not match its manifest")
        if entry.get("bytes") != len(data):
            issues.append(f"{path}: public image byte count does not match its manifest")
        if entry.get("contains_personal_paths") is not False:
            issues.append(f"{path}: public image must declare no personal paths")
        if entry.get("contains_private_controls") is not False:
            issues.append(f"{path}: public image must declare no private controls")
        source = entry.get("source")
        if path.as_posix().startswith("docs/assets/") and source != "synthetic-fixture":
            issues.append(f"{path}: public documentation screenshot must come from a synthetic fixture")
        if source not in {"synthetic-fixture", "imagegen-product-asset"}:
            issues.append(f"{path}: public image source is not allowlisted")
        if path.suffix.lower() == ".png":
            dimensions = _png_dimensions(data)
            if dimensions is None:
                issues.append(f"{path}: invalid PNG header")
            elif entry.get("width") != dimensions[0] or entry.get("height") != dimensions[1]:
                issues.append(f"{path}: public image dimensions do not match its manifest")
    return issues


def audit_repository(root: Path) -> tuple[list[str], int]:
    issues: list[str] = []
    paths = repository_paths(root)
    files: dict[PurePosixPath, bytes] = {}
    for relative_path in paths:
        full_path = root.joinpath(*relative_path.parts)
        data = full_path.read_bytes()
        files[relative_path] = data
        issues.extend(audit_bytes(relative_path, data))
    issues.extend(audit_public_images(files))
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
