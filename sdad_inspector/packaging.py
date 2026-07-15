from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .engine import RELEASE_TREE_SHA256, EngineInfo, _release_tree_digest, probe_engine
from .errors import PackageError


@dataclass(frozen=True)
class StagedEngine:
    path: Path
    engine: EngineInfo
    tree_sha256: str
    reused: bool


def _runtime_artifacts(root: Path) -> list[str]:
    artifacts: list[str] = []
    for candidate in root.rglob("*"):
        relative = candidate.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            artifacts.append(relative.as_posix())
        elif candidate.is_file() and candidate.suffix in {".pyc", ".pyo"}:
            artifacts.append(relative.as_posix())
    return sorted(set(artifacts))


def _copy_release_tree(source: Path, destination: Path) -> None:
    for candidate in sorted(source.rglob("*"), key=lambda value: value.as_posix()):
        relative = candidate.relative_to(source)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        if relative.as_posix() == ".sdad-release.json":
            continue
        if candidate.is_symlink():
            raise PackageError(
                "The authenticated SDAD source contains a symbolic link.",
                details={"path": relative.as_posix()},
            )
        if candidate.is_dir():
            (destination / relative).mkdir(parents=True, exist_ok=True)
            continue
        if not candidate.is_file() or candidate.suffix in {".pyc", ".pyo"}:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate, target)


def _write_release_marker(destination: Path, engine: EngineInfo) -> None:
    marker = {
        "doctor_version": engine.doctor_version,
        "release_tag": engine.release_tag,
        "peeled_commit": engine.revision,
        "source": engine.source,
        "tree_sha256": RELEASE_TREE_SHA256[engine.doctor_version],
    }
    (destination / ".sdad-release.json").write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _reuse_if_valid(destination: Path, source_engine: EngineInfo) -> StagedEngine | None:
    if not destination.exists():
        return None
    if not destination.is_dir() or destination.is_symlink():
        raise PackageError(
            "The engine staging destination is not a regular directory.",
            details={"path": str(destination)},
        )
    artifacts = _runtime_artifacts(destination)
    if artifacts:
        raise PackageError(
            "The engine staging destination contains runtime or repository artifacts.",
            details={"path": str(destination), "artifacts": artifacts[:20]},
        )
    try:
        staged_engine = probe_engine(destination)
    except Exception as exc:
        raise PackageError(
            "The engine staging destination already exists but is not an authenticated release tree.",
            details={"path": str(destination)},
        ) from exc
    if staged_engine.revision != source_engine.revision:
        raise PackageError(
            "The engine staging destination contains a different released engine.",
            details={
                "path": str(destination),
                "observed_revision": staged_engine.revision,
                "expected_revision": source_engine.revision,
            },
        )
    digest = _release_tree_digest(destination)
    return StagedEngine(destination, staged_engine, digest, True)


def stage_release_engine(
    checkout: str | os.PathLike[str], destination_value: str | os.PathLike[str]
) -> StagedEngine:
    """Copy one authenticated release tree without ever accepting dirty source state."""

    source_engine = probe_engine(checkout)
    source = Path(source_engine.checkout).resolve(strict=True)
    destination = Path(destination_value).expanduser().resolve(strict=False)
    try:
        destination.relative_to(source)
    except ValueError:
        pass
    else:
        raise PackageError("The engine staging destination cannot be inside its source tree.")

    reused = _reuse_if_valid(destination, source_engine)
    if reused is not None:
        return reused

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    try:
        _copy_release_tree(source, temporary)
        _write_release_marker(temporary, source_engine)
        staged_engine = probe_engine(temporary)
        artifacts = _runtime_artifacts(temporary)
        if artifacts:
            raise PackageError(
                "The staged SDAD engine gained runtime artifacts during authentication.",
                details={"artifacts": artifacts[:20]},
            )
        digest = _release_tree_digest(temporary)
        if staged_engine.revision != source_engine.revision:
            raise PackageError("The staged SDAD engine identity changed during copying.")
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    staged_engine = probe_engine(destination)
    artifacts = _runtime_artifacts(destination)
    if artifacts:
        raise PackageError(
            "The staged SDAD engine gained runtime artifacts after activation.",
            details={"artifacts": artifacts[:20]},
        )
    return StagedEngine(destination, staged_engine, digest, False)
