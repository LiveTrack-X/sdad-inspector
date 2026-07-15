#!/usr/bin/env python3
"""Validate the frozen SDAD 3.2.1/3.2.2 Packet 0 fixture contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "sdad" / "manifest.json"
CHECK_ORDER = [
    "state_schema",
    "path_integrity",
    "packet_coherence",
    "owner_gates",
    "review_state",
]
RELEASES = {
    "3.2.1": {
        "tag": "v3.2.1",
        "tag_object": "9833401b72e2913777ed860009967fdcdadcb219",
        "commit": "1ec10141782c33e6c2ea8be641a7ef95206f10bd",
    },
    "3.2.2": {
        "tag": "v3.2.2",
        "tag_object": "66b8ec1c4cfd7c1fe913190d007f3cea85a4b214",
        "commit": "cd1b1ddb3e6bcb19b531034742c7d67b4257768e",
    },
}
SCENARIOS = {
    "exit-0-state-v1-unguarded": {
        "exit_code": 0,
        "report_schema": 1,
        "state_schema": 1,
        "root": "<PROJECT_ROOT>",
        "summary": {"errors": 0, "warnings": 0},
        "checks": {"run": CHECK_ORDER, "skipped": []},
        "diagnostic_kind": None,
    },
    "exit-0-state-v2-guarded": {
        "exit_code": 0,
        "report_schema": 2,
        "state_schema": 2,
        "root": "<PROJECT_ROOT>",
        "summary": {"errors": 0, "warnings": 0},
        "checks": {"run": CHECK_ORDER, "skipped": []},
        "diagnostic_kind": None,
    },
    "exit-1-missing-state-unguarded": {
        "exit_code": 1,
        "report_schema": 1,
        "state_schema": None,
        "root": "<PROJECT_ROOT>",
        "summary": {"errors": 1, "warnings": 0},
        "checks": {"run": ["state_schema"], "skipped": CHECK_ORDER[1:]},
        "diagnostic_kind": None,
    },
    "exit-2-invalid-invocation-guarded": {
        "exit_code": 2,
        "report_schema": 2,
        "state_schema": None,
        "root": None,
        "summary": {"errors": 0, "warnings": 0},
        "checks": {"run": [], "skipped": []},
        "diagnostic_kind": "invalid_invocation",
    },
}


class ContractError(RuntimeError):
    """Packet 0 fixture contract failed."""


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _safe_fixture_path(relative: str, errors: list[str]) -> Path:
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"fixture path escapes repository root: {relative}")
    return candidate


def _validate_report(
    version: str,
    entry: dict[str, Any],
    report: dict[str, Any],
    errors: list[str],
) -> None:
    scenario = entry.get("scenario")
    expected = SCENARIOS.get(str(scenario))
    if expected is None:
        errors.append(f"{version}: unknown scenario {scenario!r}")
        return

    prefix = f"{version}/{scenario}"
    for field in ("exit_code", "report_schema", "state_schema"):
        _require(
            entry.get(field) == expected[field],
            f"{prefix}: manifest {field} mismatch",
            errors,
        )

    _require(
        report.get("schema_version") == expected["report_schema"],
        f"{prefix}: report schema mismatch",
        errors,
    )
    _require(report.get("root") == expected["root"], f"{prefix}: root was not normalized", errors)
    _require(report.get("strict") is False, f"{prefix}: unexpected strict value", errors)
    _require(report.get("summary") == expected["summary"], f"{prefix}: summary mismatch", errors)
    _require(report.get("checks") == expected["checks"], f"{prefix}: check contract mismatch", errors)

    if expected["report_schema"] == 1:
        _require("doctor_version" not in report, f"{prefix}: schema 1 exposes doctor_version", errors)
        _require("state_version" not in report, f"{prefix}: schema 1 exposes state_version", errors)
    else:
        _require(report.get("doctor_version") == version, f"{prefix}: Doctor version mismatch", errors)
        _require(
            report.get("state_version") == expected["state_schema"],
            f"{prefix}: state version mismatch",
            errors,
        )

    diagnostic_kind = expected["diagnostic_kind"]
    if diagnostic_kind is None:
        _require("diagnostic_error" not in report, f"{prefix}: unexpected diagnostic_error", errors)
    else:
        diagnostic = report.get("diagnostic_error")
        _require(isinstance(diagnostic, dict), f"{prefix}: missing diagnostic_error", errors)
        if isinstance(diagnostic, dict):
            _require(
                diagnostic.get("kind") == diagnostic_kind,
                f"{prefix}: diagnostic kind mismatch",
                errors,
            )

    if scenario == "exit-1-missing-state-unguarded":
        findings = report.get("findings")
        _require(
            isinstance(findings, list)
            and len(findings) == 1
            and findings[0].get("id") == "state.missing",
            f"{prefix}: missing-state finding contract mismatch",
            errors,
        )
    else:
        _require(report.get("findings") == [], f"{prefix}: unexpected findings", errors)

    serialized = json.dumps(report, ensure_ascii=False)
    _require("C:\\" not in serialized, f"{prefix}: Windows absolute path leaked", errors)
    _require("/Users/" not in serialized, f"{prefix}: user path leaked", errors)


def validate_manifest() -> int:
    errors: list[str] = []
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read fixture manifest: {exc}") from exc

    _require(manifest.get("schema_version") == 1, "manifest schema_version must be 1", errors)
    _require(
        manifest.get("packet_id") == "SI-001-contract-and-fixtures",
        "manifest packet_id mismatch",
        errors,
    )
    releases = manifest.get("releases")
    _require(isinstance(releases, dict), "manifest releases must be an object", errors)
    if not isinstance(releases, dict):
        raise ContractError("\n".join(errors))

    _require(set(releases) == set(RELEASES), "manifest release set mismatch", errors)
    report_count = 0
    for version, expected_release in RELEASES.items():
        release = releases.get(version)
        if not isinstance(release, dict):
            errors.append(f"{version}: release entry missing")
            continue
        for field, expected_value in expected_release.items():
            _require(
                release.get(field) == expected_value,
                f"{version}: {field} mismatch",
                errors,
            )
        _require(release.get("source_clean") is True, f"{version}: source_clean must be true", errors)
        _require(
            release.get("capture_checkout_mode") == "clean detached annotated tag",
            f"{version}: capture checkout mode mismatch",
            errors,
        )

        reports = release.get("reports")
        if not isinstance(reports, list):
            errors.append(f"{version}: reports must be a list")
            continue
        scenarios = [entry.get("scenario") for entry in reports if isinstance(entry, dict)]
        _require(set(scenarios) == set(SCENARIOS), f"{version}: scenario set mismatch", errors)
        _require(len(scenarios) == len(SCENARIOS), f"{version}: duplicate scenario", errors)

        for entry in reports:
            if not isinstance(entry, dict):
                errors.append(f"{version}: report entry must be an object")
                continue
            report_count += 1
            relative = entry.get("path")
            if not isinstance(relative, str):
                errors.append(f"{version}: report path must be a string")
                continue
            path = _safe_fixture_path(relative, errors)
            try:
                raw = path.read_bytes()
            except OSError as exc:
                errors.append(f"{version}/{entry.get('scenario')}: cannot read fixture: {exc}")
                continue
            digest = hashlib.sha256(raw).hexdigest()
            _require(digest == entry.get("sha256"), f"{relative}: SHA-256 mismatch", errors)
            try:
                report = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{relative}: invalid UTF-8 JSON: {exc}")
                continue
            if not isinstance(report, dict):
                errors.append(f"{relative}: report must be an object")
                continue
            _validate_report(version, entry, report, errors)

    _require(report_count == 8, f"expected 8 reports, found {report_count}", errors)
    if errors:
        raise ContractError("\n".join(f"- {error}" for error in errors))
    return report_count


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def verify_local_tags(repo: Path) -> None:
    errors: list[str] = []
    _require(repo.is_dir(), f"SDAD repository is not a directory: {repo}", errors)
    if errors:
        raise ContractError("\n".join(errors))
    _require(
        _git(repo, "status", "--porcelain", "--untracked-files=no") == "",
        "provided SDAD worktree is dirty",
        errors,
    )
    for version, expected in RELEASES.items():
        tag = expected["tag"]
        _require(_git(repo, "cat-file", "-t", tag) == "tag", f"{tag} is not annotated", errors)
        _require(_git(repo, "rev-parse", tag) == expected["tag_object"], f"{tag} object mismatch", errors)
        _require(
            _git(repo, "rev-parse", f"{tag}^{{}}") == expected["commit"],
            f"{tag} peeled commit mismatch",
            errors,
        )
    if errors:
        raise ContractError("\n".join(f"- {error}" for error in errors))


def _archive_tag(repo: Path, tag: str, destination: Path) -> None:
    archive = destination.parent / f"{tag}.zip"
    result = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=zip", "-o", str(archive), tag],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(f"git archive {tag} failed: {result.stderr.strip()}")
    destination.mkdir(parents=True)
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            candidate = (destination / member.filename).resolve()
            try:
                candidate.relative_to(destination_root)
            except ValueError as exc:
                raise ContractError(f"unsafe archive member in {tag}: {member.filename}") from exc
        bundle.extractall(destination)


def _scenario_arguments(version: str, scenario: str) -> list[str]:
    projects = ROOT / "tests" / "fixture-projects"
    if scenario == "exit-0-state-v1-unguarded":
        return ["doctor", str(projects / "state-v1"), "--json"]
    if scenario == "exit-0-state-v2-guarded":
        return [
            "doctor",
            str(projects / "state-v2"),
            "--require-version",
            version,
            "--json",
        ]
    if scenario == "exit-1-missing-state-unguarded":
        return ["doctor", str(projects / "missing-state"), "--json"]
    if scenario == "exit-2-invalid-invocation-guarded":
        return [
            "doctor",
            str(projects / "state-v2"),
            "--require-version",
            version,
            "--json",
            "--unknown",
        ]
    raise ContractError(f"cannot recapture unknown scenario: {scenario}")


def recapture_tagged_reports(repo: Path) -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    compared = 0
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="sdad-packet-0-") as temporary:
        temp_root = Path(temporary)
        for version, release in manifest["releases"].items():
            engine_root = temp_root / f"engine-{version}"
            _archive_tag(repo, release["tag"], engine_root)
            script = engine_root / "scripts" / "sdad.py"
            for entry in release["reports"]:
                scenario = entry["scenario"]
                result = subprocess.run(
                    [sys.executable, str(script), *_scenario_arguments(version, scenario)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                prefix = f"{version}/{scenario}"
                _require(
                    result.returncode == entry["exit_code"],
                    f"{prefix}: recapture exit {result.returncode}, expected {entry['exit_code']}",
                    errors,
                )
                _require(result.stderr == "", f"{prefix}: recapture wrote stderr", errors)
                try:
                    observed = json.loads(result.stdout)
                except json.JSONDecodeError as exc:
                    errors.append(f"{prefix}: recapture emitted invalid JSON: {exc}")
                    continue
                if observed.get("root") is not None:
                    observed["root"] = "<PROJECT_ROOT>"
                expected_path = _safe_fixture_path(entry["path"], errors)
                expected = json.loads(expected_path.read_text(encoding="utf-8"))
                _require(observed == expected, f"{prefix}: recapture differs from golden report", errors)
                compared += 1
    if errors:
        raise ContractError("\n".join(f"- {error}" for error in errors))
    return compared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdad-repo",
        type=Path,
        help="Also verify local annotated tag objects and require a clean SDAD worktree.",
    )
    parser.add_argument(
        "--recapture",
        action="store_true",
        help="Re-run all eight scenarios from git archives of the released tags.",
    )
    args = parser.parse_args(argv)
    if args.recapture and args.sdad_repo is None:
        parser.error("--recapture requires --sdad-repo")
    try:
        count = validate_manifest()
        if args.sdad_repo is not None:
            verify_local_tags(args.sdad_repo.resolve())
        recaptured = (
            recapture_tagged_reports(args.sdad_repo.resolve())
            if args.recapture and args.sdad_repo is not None
            else 0
        )
    except ContractError as exc:
        print(f"Packet 0 contract FAILED:\n{exc}", file=sys.stderr)
        return 1
    suffix = ""
    if args.sdad_repo is not None:
        suffix += " and local tag objects"
    if recaptured:
        suffix += f"; {recaptured} live tagged reports matched"
    print(f"Packet 0 contract OK: 2 releases, {count} normalized reports{suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
