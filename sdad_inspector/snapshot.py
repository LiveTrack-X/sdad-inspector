from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from . import __version__
from .adapters import adapt_doctor_report
from .engine import EngineInfo, probe_engine, run_doctor
from .paths import canonical_directory, control_fingerprint
from .state import load_control_state, peek_control_paths

SNAPSHOT_SCHEMA_VERSION = 1
ProgressCallback = Callable[[str, str, str], None]


def _progress(
    callback: ProgressCallback | None,
    stage: str,
    source: str,
    event: str,
) -> None:
    if callback is not None:
        callback(stage, source, event)


def _project_identity(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]


def _relationships(state: dict[str, Any]) -> list[dict[str, Any]]:
    packet = state.get("active_packet") or {}
    spec = state.get("active_spec") or {}
    handoff = state.get("current_handoff") or {}
    return [
        {
            "kind": "active_spec_to_packet",
            "from": spec.get("path"),
            "to": packet.get("id"),
            "status": "declared" if spec.get("path") and packet.get("id") else "missing",
        },
        {
            "kind": "validation_for_packet",
            "from": state.get("validation_for"),
            "to": packet.get("id"),
            "status": "matches"
            if state.get("validation_for") == packet.get("id") and packet.get("id")
            else "not_declared"
            if state.get("validation_for") is None
            else "mismatch",
        },
        {
            "kind": "handoff_to_packet",
            "from": handoff.get("path"),
            "to": packet.get("id"),
            "status": "present" if handoff.get("exists") else "absent",
        },
    ]


def inspect_project(
    project_root: str | Path,
    sdad_checkout: str | Path,
    *,
    timeout: float = 30,
    strict: bool = True,
    _engine_info: EngineInfo | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    root = canonical_directory(project_root, label="Project root")
    _progress(progress_callback, "prepare", ".", "project_boundary_ready")
    engine = _engine_info or probe_engine(sdad_checkout, timeout=min(timeout, 10))
    watched_paths = peek_control_paths(root)
    before = control_fingerprint(root, watched_paths)

    _progress(progress_callback, "doctor", "scripts/sdad.py", "doctor_started")
    doctor_run = run_doctor(engine, root, timeout=timeout, strict=strict)
    doctor = adapt_doctor_report(
        doctor_run.report,
        engine_version=engine.doctor_version,
        expected_root=root,
    )
    _progress(progress_callback, "doctor", "scripts/sdad.py", "doctor_completed")
    state, evidence_files = load_control_state(
        root,
        observer=lambda source: _progress(
            progress_callback, "controls", source, "control_source_read"
        ),
    )
    _progress(
        progress_callback,
        "integrity",
        f"{len(watched_paths)} bounded control sources",
        "integrity_check_started",
    )
    after = control_fingerprint(root, watched_paths)
    unchanged = before == after
    diagnostic = doctor.get("diagnostic_error")
    status = "diagnostic" if diagnostic else "completed"
    limitations = [
        "Declared validation commands are presented but never executed.",
        "Only bounded SDAD control files are read; private corpora and secret files are excluded.",
        "Local inspection does not establish Windows, macOS, Linux, packaging, or release support.",
    ]
    if not unchanged:
        status = "stale"
        limitations.append(
            "One or more watched control files changed during inspection; re-scan before relying on this snapshot."
        )

    _progress(
        progress_callback,
        "report",
        "Inspector snapshot (memory)",
        "snapshot_assembly_started",
    )
    inspected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    snapshot = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "inspector_version": __version__,
        "inspection_id": str(uuid4()),
        "inspected_at": inspected_at,
        "inspection_status": status,
        "read_only": True,
        "project": {
            "root": str(root),
            "name": root.name,
            "identity": _project_identity(root),
        },
        "engine": engine.to_dict(),
        "contracts": {
            "doctor_version": engine.doctor_version,
            "report_schema_version": doctor["report_schema_version"],
            "state_schema_version": state.get("schema_version"),
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        },
        "doctor": {
            **doctor,
            "exit_code": doctor_run.exit_code,
            "completed": doctor_run.exit_code in {0, 1} and diagnostic is None,
            "argv_shape": doctor_run.argv_shape,
            "stderr_present": doctor_run.stderr_present,
        },
        "state": state,
        "relationships": _relationships(state),
        "integrity": {
            "watched_control_paths": watched_paths,
            "control_files_unchanged_during_inspection": unchanged,
            "before": before,
            "after": after,
        },
        "evidence": {
            "files": evidence_files,
            "doctor_report": doctor_run.report,
            "doctor_exit_code": doctor_run.exit_code,
        },
        "limitations": limitations,
    }
    # Round-trip now so callers never receive non-JSON values from YAML.
    json.dumps(snapshot, ensure_ascii=False)
    _progress(
        progress_callback,
        "report",
        "Inspector snapshot (memory)",
        "snapshot_serialized",
    )
    return snapshot
