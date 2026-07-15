from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "0.0.1a1"
RELEASE_VERSION = "0.0.1-alpha.1"
RELEASE_TAG = f"v{RELEASE_VERSION}"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _require(issues: list[str], text: str, needle: str, *, source: str) -> None:
    if needle not in text:
        issues.append(f"{source}: missing required release contract {needle!r}")


def _tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return {
        value.decode("utf-8").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    }


def validate_release_contract() -> list[str]:
    issues: list[str] = []
    pyproject = _read("pyproject.toml")
    package = _read("sdad_inspector/__init__.py")
    readme = _read("README.md")
    workflow = _read(".github/workflows/release.yml")
    notes = _read("docs/releases/v0.0.1-alpha.1.md")
    ignore = _read(".gitignore")
    packager = _read("scripts/package_release.py")
    native_builder = _read("scripts/build_native.py")
    native_spec = _read("packaging/sdad-inspector.spec")
    portable_smoke = _read("scripts/smoke_release_archive.py")

    if not re.search(rf'^version = "{re.escape(PACKAGE_VERSION)}"$', pyproject, re.MULTILINE):
        issues.append(f"pyproject.toml: project version is not {PACKAGE_VERSION}")
    if f'__version__ = "{PACKAGE_VERSION}"' not in package:
        issues.append(f"sdad_inspector/__init__.py: package version is not {PACKAGE_VERSION}")

    for needle in (
        RELEASE_TAG,
        "0.0.1 alpha is experimental and unsigned",
        "Which SDAD projects can it inspect?",
        "Official SDAD Protocol `v3.2.2`",
        "Windows",
        "macOS",
        "Linux",
        "SHA256SUMS",
        "single portable executable",
    ):
        _require(issues, readme, needle, source="README.md")

    for needle in (
        RELEASE_TAG,
        "windows-latest",
        "macos-latest",
        "ubuntu-latest",
        "actions/upload-artifact@v4",
        "actions/download-artifact@v4",
        "scripts/package_release.py",
        "portable-smoke",
        "scripts/smoke_release_archive.py",
        'python-version: "3.12"',
        "needs: [build, portable-smoke]",
        "scripts/write_checksums.py",
        "--prerelease",
        "contents: write",
    ):
        _require(issues, workflow, needle, source=".github/workflows/release.yml")

    for needle in (
        "# SDAD Inspector 0.0.1 alpha",
        "Unsigned alpha",
        "exact `v0.0.1-alpha.1` tag",
        "SHA256SUMS",
        "SDAD Protocol `v3.2.2`",
        "single portable executable",
    ):
        _require(issues, notes, needle, source="docs/releases/v0.0.1-alpha.1.md")

    for needle in ("design/qa/", "design-qa.md", "web/.npmrc", "release-artifacts/"):
        _require(issues, ignore, needle, source=".gitignore")
    for needle in (
        "windows",
        "macos",
        "linux",
        ".zip",
        ".tar.gz",
        '"archive_member_count": 1',
        '"unsigned-one-file-portable"',
    ):
        _require(issues, packager, needle, source="scripts/package_release.py")
    for needle in ("CPython 3.12", 'version != (3, 12)', "require_release_python"):
        _require(issues, native_builder, needle, source="scripts/build_native.py")
    for needle in ("analysis.binaries", "analysis.datas", '"webview"'):
        _require(issues, native_spec, needle, source="packaging/sdad-inspector.spec")
    for forbidden in ("COLLECT(", "BUNDLE(", "exclude_binaries=True"):
        if forbidden in native_spec:
            issues.append(f"packaging/sdad-inspector.spec: one-folder construct {forbidden!r}")
    for needle in (
        "extract_single_executable",
        "archive_member_count",
        "python_runtime_installed_for_product",
    ):
        _require(issues, portable_smoke, needle, source="scripts/smoke_release_archive.py")

    tracked = _tracked_paths()
    forbidden = sorted(
        path
        for path in tracked
        if path in {"design-qa.md", "web/.npmrc"} or path.startswith("design/qa/")
    )
    if forbidden:
        issues.append("tracked local-only release files: " + ", ".join(forbidden))
    return issues


def main() -> int:
    issues = validate_release_contract()
    if issues:
        print("Release contract validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(
        "Release contract validation passed: "
        f"package {PACKAGE_VERSION}, tag {RELEASE_TAG}, 3 unsigned single-file platform archives"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
