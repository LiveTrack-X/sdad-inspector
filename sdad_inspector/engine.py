from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .errors import DoctorOutputError, EngineError, UnsupportedContractError
from .paths import canonical_directory

SUPPORTED_DOCTOR_VERSIONS = ("3.2.1", "3.2.2")
RELEASE_COMMITS = {
    "3.2.1": "1ec10141782c33e6c2ea8be641a7ef95206f10bd",
    "3.2.2": "cd1b1ddb3e6bcb19b531034742c7d67b4257768e",
}
RELEASE_TREE_SHA256 = {
    "3.2.1": "0e2bc4324cf247c173b1b5fdbb711c3ccbd2e46b02e0108b01bb16a4ef8b44cb",
    "3.2.2": "a2658b011844a5ee4f3683a90bac3d8135da56579aecf29ef4f3b031ddf79401",
}
MAX_DOCTOR_OUTPUT_BYTES = 1024 * 1024
RELEASE_TEXT_SUFFIXES = {
    ".html",
    ".json",
    ".md",
    ".mdc",
    ".ps1",
    ".py",
    ".sh",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
}
RELEASE_TEXT_NAMES = {".gitattributes", ".gitignore", "LICENSE"}


@dataclass(frozen=True)
class EngineInfo:
    checkout: str
    doctor_version: str
    release_tag: str
    revision: str
    source: str | None
    trust: str
    clean: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DoctorRun:
    exit_code: int
    argv_shape: list[str]
    report: dict[str, Any]
    stderr_present: bool


def _run(
    argv: list[str], *, timeout: float, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            argv,
            cwd=cwd,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise EngineError(
            "The SDAD engine timed out.", details={"timeout_seconds": timeout}
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise EngineError("The SDAD engine could not be started safely.") from exc


def _read_release_marker(checkout: Path) -> dict[str, Any] | None:
    marker = checkout / ".sdad-release.json"
    if not marker.is_file() or marker.is_symlink():
        return None
    try:
        payload = json.loads(marker.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EngineError("The SDAD release marker is unreadable.") from exc
    if not isinstance(payload, dict):
        raise EngineError("The SDAD release marker is not an object.")
    return payload


def _git_value(checkout: Path, *arguments: str) -> str | None:
    result = _run(["git", "-C", str(checkout), *arguments], timeout=10)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _release_tree_digest(checkout: Path) -> str:
    digest = hashlib.sha256()
    files: list[Path] = []
    for path in checkout.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(checkout)
        if relative.as_posix() == ".sdad-release.json":
            continue
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise EngineError("The SDAD release archive contains a symbolic link.")
        files.append(path)
    for path in sorted(files, key=lambda value: value.relative_to(checkout).as_posix()):
        relative_path = path.relative_to(checkout)
        relative = relative_path.as_posix()
        content = path.read_bytes()
        if (
            relative_path.suffix.casefold() in RELEASE_TEXT_SUFFIXES
            or relative_path.name in RELEASE_TEXT_NAMES
        ):
            content = content.replace(b"\r\n", b"\n")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def _validated_entrypoint(checkout: Path) -> Path:
    script = checkout / "scripts" / "sdad.py"
    if script.is_symlink() or not script.is_file():
        raise EngineError(
            "The selected checkout does not contain a regular scripts/sdad.py file.",
            details={"checkout": str(checkout)},
        )
    try:
        script.resolve(strict=True).relative_to(checkout)
    except (OSError, RuntimeError, ValueError) as exc:
        raise EngineError("The SDAD entrypoint escapes the selected checkout.") from exc
    return script


def authenticate_release_archive(checkout_value: str | Path) -> EngineInfo:
    """Authenticate a marker-backed release tree without executing its code."""

    checkout = canonical_directory(checkout_value, label="SDAD checkout")
    _validated_entrypoint(checkout)
    marker = _read_release_marker(checkout)
    if marker is None:
        raise EngineError(
            "The bundled SDAD engine is missing its release marker.",
            details={"checkout": str(checkout)},
        )
    marker_version = marker.get("doctor_version")
    if marker_version not in SUPPORTED_DOCTOR_VERSIONS:
        raise UnsupportedContractError(
            "This Doctor core is not supported.",
            details={
                "observed": marker_version,
                "supported": list(SUPPORTED_DOCTOR_VERSIONS),
            },
        )
    version = str(marker_version)
    expected_commit = RELEASE_COMMITS[version]
    expected_tag = f"v{version}"
    marker_tag = marker.get("release_tag")
    marker_commit = marker.get("peeled_commit")
    if (marker_version, marker_tag, marker_commit) != (
        version,
        expected_tag,
        expected_commit,
    ):
        raise EngineError(
            "The SDAD release marker does not match the supported release contract.",
            details={"observed_version": version, "expected_tag": expected_tag},
        )
    tree_digest = _release_tree_digest(checkout)
    if tree_digest != RELEASE_TREE_SHA256[version]:
        raise EngineError(
            "The SDAD release archive does not match the frozen release tree.",
            details={
                "observed_tree_sha256": tree_digest,
                "expected_tree_sha256": RELEASE_TREE_SHA256[version],
            },
        )
    return EngineInfo(
        checkout=str(checkout),
        doctor_version=version,
        release_tag=expected_tag,
        revision=expected_commit,
        source=str(marker.get("source")) if marker.get("source") else None,
        trust="release-marker",
        clean=True,
    )


def _engine_argv(script: Path, *arguments: str) -> list[str]:
    if not getattr(sys, "frozen", False):
        return [sys.executable, "-I", "-B", str(script), *arguments]
    bundled = Path(__file__).resolve().parents[1] / "sdad-engine" / "scripts" / "sdad.py"
    try:
        is_bundled = script.resolve(strict=True) == bundled.resolve(strict=True)
    except OSError:
        is_bundled = False
    if not is_bundled:
        raise EngineError(
            "The frozen preview only executes its authenticated bundled SDAD engine."
        )
    return [sys.executable, "--sdad-internal-engine", *arguments]


def probe_engine(checkout_value: str | Path, *, timeout: float = 10) -> EngineInfo:
    checkout = canonical_directory(checkout_value, label="SDAD checkout")
    script = _validated_entrypoint(checkout)

    marker = _read_release_marker(checkout)
    if marker is not None:
        authenticated = authenticate_release_archive(checkout)
        version = authenticated.doctor_version
        version_result = _run(
            _engine_argv(script, "--version"), timeout=timeout
        )
        observed_version = version_result.stdout.strip()
        if version_result.returncode != 0 or observed_version != version:
            raise EngineError("The authenticated SDAD engine returned a different version.")
        return authenticated

    revision = _git_value(checkout, "rev-parse", "HEAD")
    status = _git_value(checkout, "status", "--porcelain=v1")
    reverse_commits = {commit: version for version, commit in RELEASE_COMMITS.items()}
    version = reverse_commits.get(revision or "")
    if version is None:
        raise EngineError(
            "The selected checkout is not at the supported released commit.",
            details={
                "observed_revision": revision,
                "supported_revisions": sorted(RELEASE_COMMITS.values()),
            },
        )
    if status is None or status:
        raise EngineError(
            "The selected SDAD checkout is dirty or its clean state cannot be proven.",
            details={"release_tag": f"v{version}"},
        )
    version_result = _run(_engine_argv(script, "--version"), timeout=timeout)
    if version_result.returncode != 0 or version_result.stdout.strip() != version:
        raise EngineError("The authenticated SDAD checkout returned a different version.")
    return EngineInfo(
        checkout=str(checkout),
        doctor_version=version,
        release_tag=f"v{version}",
        revision=revision,
        source=_git_value(checkout, "remote", "get-url", "origin"),
        trust="clean-tag-commit",
        clean=True,
    )


def run_doctor(
    engine: EngineInfo,
    project_root: Path,
    *,
    timeout: float = 30,
    strict: bool = True,
) -> DoctorRun:
    script = Path(engine.checkout) / "scripts" / "sdad.py"
    doctor_arguments = [
        "doctor",
        str(project_root),
        "--json",
    ]
    if strict:
        doctor_arguments.append("--strict")
    doctor_arguments.extend(["--require-version", engine.doctor_version])
    argv = _engine_argv(script, *doctor_arguments)
    result = _run(argv, timeout=timeout)
    if result.returncode not in {0, 1, 2}:
        raise DoctorOutputError(
            "Doctor returned an unsupported process exit code.",
            details={"exit_code": result.returncode},
        )
    encoded = result.stdout.encode("utf-8")
    if len(encoded) > MAX_DOCTOR_OUTPUT_BYTES:
        raise DoctorOutputError(
            "Doctor output exceeded the inspection budget.",
            details={"bytes": len(encoded)},
        )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DoctorOutputError(
            "Doctor returned malformed or truncated JSON.",
            details={"line": exc.lineno, "column": exc.colno},
        ) from exc
    if not isinstance(report, dict):
        raise DoctorOutputError("Doctor JSON must be one object.")
    diagnostic = report.get("diagnostic_error")
    if result.returncode == 2 and not isinstance(diagnostic, dict):
        raise DoctorOutputError("Doctor exit 2 did not include a diagnostic_error object.")
    if result.returncode in {0, 1} and diagnostic is not None:
        raise DoctorOutputError("A completed Doctor run included a diagnostic_error.")
    return DoctorRun(
        exit_code=result.returncode,
        argv_shape=["python", "scripts/sdad.py", "doctor", "<PROJECT_ROOT>", "--json"]
        + (["--strict"] if strict else [])
        + ["--require-version", engine.doctor_version],
        report=report,
        stderr_present=bool(result.stderr.strip()),
    )
