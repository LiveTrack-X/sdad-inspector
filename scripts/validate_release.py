from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "0.0.3"
RELEASE_VERSION = "0.0.3"
RELEASE_TAG = f"v{RELEASE_VERSION}"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _require(issues: list[str], text: str, needle: str, *, source: str) -> None:
    if needle not in text:
        issues.append(f"{source}: missing required release contract {needle!r}")


def _tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
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
    korean_readme = _read("README.ko.md")
    japanese_readme = _read("README.ja.md")
    chinese_readme = _read("README.zh-CN.md")
    license_text = _read("LICENSE")
    funding = _read(".github/FUNDING.yml")
    workflow = _read(".github/workflows/release.yml")
    cross_platform_workflow = _read(".github/workflows/cross-platform.yml")
    notes = _read("docs/releases/v0.0.3.md")
    ignore = _read(".gitignore")
    packager = _read("scripts/package_release.py")
    native_builder = _read("scripts/build_native.py")
    native_spec = _read("packaging/sdad-inspector.spec")
    version_info = _read("packaging/sdad-inspector-version.txt")
    windows_branding = _read("scripts/validate_windows_branding.py")
    portable_smoke = _read("scripts/smoke_release_archive.py")
    updater = _read("sdad_inspector/updater.py")
    overview = _read("web/src/components/Overview.tsx")
    web_package = json.loads(_read("web/package.json"))

    if not re.search(rf'^version = "{re.escape(PACKAGE_VERSION)}"$', pyproject, re.MULTILINE):
        issues.append(f"pyproject.toml: project version is not {PACKAGE_VERSION}")
    if f'__version__ = "{PACKAGE_VERSION}"' not in package:
        issues.append(f"sdad_inspector/__init__.py: package version is not {PACKAGE_VERSION}")
    for needle in ('license = "MIT"', 'license-files = ["LICENSE"]'):
        _require(issues, pyproject, needle, source="pyproject.toml")

    for needle in (
        RELEASE_TAG,
        "0.0.3 is a regular GitHub Release, but remains unsigned",
        "web/public/sdad-inspector-banner.png",
        "Which SDAD projects can it inspect?",
        "Official SDAD Protocol `v3.2.2`",
        "official-sdad-3",
        "Inspector snapshot schema | 2",
        "Windows",
        "macOS",
        "Linux",
        "SHA256SUMS",
        "single portable executable",
        "[한국어](README.ko.md)",
        "[日本語](README.ja.md)",
        "[简体中文](README.zh-CN.md)",
        "MIT License",
        "GitHub Sponsors",
    ):
        _require(issues, readme, needle, source="README.md")
    localized_readmes = {
        "README.ko.md": korean_readme,
        "README.ja.md": japanese_readme,
        "README.zh-CN.md": chinese_readme,
    }
    for source, localized_readme in localized_readmes.items():
        for needle in (
            "[English](README.md)",
            "[한국어](README.ko.md)",
            "[日本語](README.ja.md)",
            "[简体中文](README.zh-CN.md)",
            RELEASE_TAG,
            "SHA256SUMS",
            "MIT License",
            "GitHub Sponsors",
        ):
            _require(issues, localized_readme, needle, source=source)

    for needle in ("MIT License", "Copyright (c) 2026 LiveTrack-X", "THE SOFTWARE IS PROVIDED \"AS IS\""):
        _require(issues, license_text, needle, source="LICENSE")
    _require(issues, funding, "github: [LiveTrack-X]", source=".github/FUNDING.yml")

    for needle in (
        RELEASE_TAG,
        "windows-latest",
        "macos-latest",
        "ubuntu-latest",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "scripts/package_release.py",
        "portable-smoke",
        "scripts/smoke_release_archive.py",
        "python scripts/validate_browser_contract.py --sdad-checkout .ci/sdad-v3.2.2",
        "python scripts/validate_static_report.py --sdad-checkout .ci/sdad-v3.2.2",
        'python-version: "3.12"',
        "needs: [build, portable-smoke]",
        "scripts/write_checksums.py",
        "--draft",
        "--draft=false",
        "--latest",
        "actions/attest@v4",
        "id-token: write",
        "attestations: write",
        "contents: write",
        "npm --prefix web audit --audit-level=high",
    ):
        _require(issues, workflow, needle, source=".github/workflows/release.yml")
    if "--clobber" in workflow:
        issues.append(".github/workflows/release.yml: immutable release assets may not be refreshed with --clobber")
    if "--prerelease" in workflow:
        issues.append(".github/workflows/release.yml: v0.0.3 must publish as a regular release")
    for needle in (
        f'--version "{RELEASE_VERSION}"',
        "windows-latest",
        "macos-latest",
        "ubuntu-latest",
        "portable-smoke",
    ):
        _require(
            issues,
            cross_platform_workflow,
            needle,
            source=".github/workflows/cross-platform.yml",
        )

    for needle in (
        "# SDAD Inspector 0.0.3",
        "Unsigned portable release",
        "exact `v0.0.3` tag",
        "SHA256SUMS",
        "SDAD Protocol `v3.2.2`",
        "single portable executable",
        "automatic product update",
        "successful-update acknowledgement",
        "Japanese",
        "Simplified Chinese",
        "UI scale",
        "MIT License",
        "GitHub Sponsors",
        "ProtocolAdapter",
        "Snapshot schema 2",
        "exact executable path",
    ):
        _require(issues, notes, needle, source="docs/releases/v0.0.3.md")

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
    for needle in ("analysis.binaries", "analysis.datas", '"webview"', "sdad-inspector.ico", "sdad-inspector.icns", "icon=ICON", "version=VERSION_INFO"):
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
    for needle in (
        'release.get("immutable") is not True',
        "asset_sha256",
        "INTERNAL_UPDATE_FLAG",
        "apply_update_plan",
        "PARENT_EXIT_TIMEOUT_SECONDS",
    ):
        _require(issues, updater, needle, source="sdad_inspector/updater.py")

    for needle in (
        "FileDescription', 'SDAD Inspector'",
        "ProductName', 'SDAD Inspector'",
        "FileVersion', '0.0.3.0'",
        "ProductVersion', '0.0.3'",
        "OriginalFilename', 'SDAD-Inspector.exe'",
    ):
        _require(issues, version_info, needle, source="packaging/sdad-inspector-version.txt")
    for needle in (
        'pefile.RESOURCE_TYPE["RT_ICON"]',
        "packaging/sdad-inspector.ico",
        'b"ProductVersion": b"0.0.3"',
        '"icon": "matches-source"',
    ):
        _require(issues, windows_branding, needle, source="scripts/validate_windows_branding.py")
    for forbidden_overview_art in ("/sdad-inspector-banner.png", "product-banner"):
        if forbidden_overview_art in overview:
            issues.append(
                "web/src/components/Overview.tsx: README-only banner must not render in the app"
            )

    vite_raw = str((web_package.get("dependencies") or {}).get("vite") or "")
    vite_match = re.fullmatch(r"[~^]?(\d+)\.(\d+)\.(\d+)", vite_raw)
    if not vite_match or tuple(map(int, vite_match.groups())) < (6, 4, 3):
        issues.append("web/package.json: Vite must be locked at 6.4.3 or later")

    tracked = _tracked_paths()
    forbidden = sorted(
        path
        for path in tracked
        if path in {"design-qa.md", "web/.npmrc"} or path.startswith("design/qa/")
    )
    if forbidden:
        issues.append("tracked local-only release files: " + ", ".join(forbidden))
    for required_asset in (
        "LICENSE",
        ".github/FUNDING.yml",
        "README.ko.md",
        "README.ja.md",
        "README.zh-CN.md",
        "web/public/sdad-inspector-logo.png",
        "packaging/sdad-inspector.ico",
        "packaging/sdad-inspector.icns",
        "packaging/sdad-inspector-version.txt",
        "web/public/sdad-inspector-banner.png",
        "scripts/validate_windows_branding.py",
    ):
        if required_asset not in tracked:
            issues.append(f"missing tracked brand asset: {required_asset}")
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
        f"package {PACKAGE_VERSION}, regular tag {RELEASE_TAG}, 3 unsigned single-file platform archives"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
