from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import yaml

from .errors import BoundedReadError, InspectorError, UnsupportedContractError
from .paths import file_metadata, read_bounded_text, safe_project_path

SUPPORTED_STATE_SCHEMAS = (1, 2)
_TODO_PATTERN = re.compile(r"^- \[ \] \[packet:[A-Za-z0-9._-]+\] .+")
_FINDING_PATTERN = re.compile(
    r"^- \[(Critical|High|Medium|Low)\] \[packet:[A-Za-z0-9._-]+\] .+"
)
ReadObserver = Callable[[str], None]


def _observe(observer: ReadObserver | None, relative: str) -> None:
    if observer is not None:
        observer(relative)


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BoundedReadError(f"State field {field} must be a mapping.")
    return value


def _string(value: Any, *, field: str, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise BoundedReadError(f"State field {field} must be a non-empty string.")
    return value


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise BoundedReadError(f"State field {field} must be a string list.")
    return list(value)


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BoundedReadError("sdad-state.yaml is malformed YAML.") from exc
    return _mapping(value, field="root")


def peek_control_paths(root: Path) -> list[str]:
    paths = ["sdad-state.yaml", "docs/TODO-Open-Items.md", "review-findings.md"]
    text = read_bounded_text(
        root, "sdad-state.yaml", purpose="SDAD state", required=False
    )
    if text is None:
        return paths
    try:
        state = _load_yaml(text)
    except BoundedReadError:
        return paths
    for key in ("active_spec", "current_handoff"):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            try:
                safe_project_path(root, value, purpose=key, must_exist=False)
            except Exception:
                continue
            paths.append(value)
    return paths


def _active_section(text: str | None, heading: str) -> list[str]:
    if not text:
        return []
    active = False
    lines: list[str] = []
    for line in text.splitlines():
        if line == heading:
            active = True
            continue
        if active and line.startswith("## "):
            break
        if active:
            lines.append(line)
    return lines


def _ledger_summary(root: Path, observer: ReadObserver | None = None) -> dict[str, Any]:
    _observe(observer, "docs/TODO-Open-Items.md")
    todo_text = read_bounded_text(
        root,
        "docs/TODO-Open-Items.md",
        purpose="active TODO ledger",
        required=False,
    )
    _observe(observer, "review-findings.md")
    findings_text = read_bounded_text(
        root,
        "review-findings.md",
        purpose="active review ledger",
        required=False,
    )
    todo_lines = _active_section(todo_text, "## Active Work")
    finding_lines = _active_section(findings_text, "## Active Findings")
    todos = [line for line in todo_lines if _TODO_PATTERN.match(line)]
    findings = [line for line in finding_lines if _FINDING_PATTERN.match(line)]
    severity = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for line in findings:
        match = _FINDING_PATTERN.match(line)
        if match:
            severity[match.group(1)] += 1
    return {
        "todo_open": len(todos),
        "review_findings_open": len(findings),
        "review_findings_by_severity": severity,
    }


def load_control_state(
    root: Path,
    *,
    observer: ReadObserver | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, object]]]:
    _observe(observer, "sdad-state.yaml")
    text = read_bounded_text(
        root, "sdad-state.yaml", purpose="SDAD state", required=False
    )
    if text is None:
        state = {
            "available": False,
            "schema_version": None,
            "active_spec": None,
            "active_packet": None,
            "validation_for": None,
            "validation": [],
            "owner_gates": [],
            "routed_docs": [],
            "current_handoff": None,
            "ledger": _ledger_summary(root, observer),
        }
        return state, {"sdad-state.yaml": file_metadata(root, "sdad-state.yaml")}

    raw = _load_yaml(text)
    version = raw.get("version")
    if version not in SUPPORTED_STATE_SCHEMAS:
        raise UnsupportedContractError(
            "This SDAD state schema is not supported.",
            details={"observed": version, "supported": list(SUPPORTED_STATE_SCHEMAS)},
        )
    packet = _mapping(raw.get("active_packet"), field="active_packet")
    active_packet = {
        "id": _string(packet.get("id"), field="active_packet.id"),
        "objective": _string(packet.get("objective"), field="active_packet.objective"),
        "status": _string(packet.get("status"), field="active_packet.status"),
    }
    active_spec = _string(raw.get("active_spec"), field="active_spec")
    assert active_spec is not None
    active_spec_path = safe_project_path(
        root, active_spec, purpose="active SPEC", must_exist=False
    )
    handoff = _string(raw.get("current_handoff"), field="current_handoff", optional=True)
    handoff_status: dict[str, Any]
    if handoff:
        handoff_path = safe_project_path(
            root, handoff, purpose="current handoff", must_exist=False
        )
        handoff_status = {
            "path": handoff,
            "declared": True,
            "exists": handoff_path.is_file(),
        }
    else:
        handoff_status = {"path": None, "declared": False, "exists": False}

    validation_raw = raw.get("validation")
    if validation_raw is None:
        validation_raw = []
    if not isinstance(validation_raw, list):
        raise BoundedReadError("State field validation must be a list.")
    validation: list[dict[str, str]] = []
    for index, item in enumerate(validation_raw):
        record = _mapping(item, field=f"validation[{index}]")
        command = _string(record.get("command"), field=f"validation[{index}].command")
        proves = _string(record.get("proves"), field=f"validation[{index}].proves")
        assert command is not None and proves is not None
        validation.append({"command": command, "proves": proves, "executed": False})

    evidence: dict[str, dict[str, object]] = {}
    for evidence_path in (
        "sdad-state.yaml",
        active_spec,
        "docs/TODO-Open-Items.md",
        "review-findings.md",
    ):
        _observe(observer, evidence_path)
        evidence[evidence_path] = file_metadata(root, evidence_path)
    if handoff:
        _observe(observer, handoff)
        evidence[handoff] = file_metadata(root, handoff)

    state = {
        "available": True,
        "schema_version": version,
        "updated": str(raw.get("updated")) if raw.get("updated") is not None else None,
        "scale": raw.get("scale"),
        "execution_scope": raw.get("execution_scope") if version == 2 else None,
        "legacy_controls": {
            "intensity": raw.get("intensity") if version == 1 else None,
            "autonomy": raw.get("autonomy") if version == 1 else None,
        },
        "active_spec": {
            "path": active_spec,
            "exists": active_spec_path.is_file(),
        },
        "active_packet": active_packet,
        "validation_for": raw.get("validation_for") if version == 2 else None,
        "validation": validation,
        "owner_gates": _string_list(raw.get("owner_gates"), field="owner_gates"),
        "routed_docs": _string_list(raw.get("routed_docs"), field="routed_docs"),
        "current_handoff": handoff_status,
        "ledger": _ledger_summary(root, observer),
    }
    return state, evidence


def load_live_documents(root: Path) -> dict[str, Any]:
    """Read only state-declared Markdown surfaces through existing path budgets."""

    state, _ = load_control_state(root)
    roles: dict[str, list[str]] = {
        "docs/TODO-Open-Items.md": ["todo"],
        "review-findings.md": ["findings"],
    }
    active_spec = state.get("active_spec") or {}
    if isinstance(active_spec.get("path"), str):
        roles.setdefault(active_spec["path"], []).append("active_spec")
    handoff = state.get("current_handoff") or {}
    if handoff.get("declared") and isinstance(handoff.get("path"), str):
        roles.setdefault(handoff["path"], []).append("current_handoff")
    for routed in state.get("routed_docs") or []:
        if isinstance(routed, str) and routed.casefold().endswith(".md"):
            roles.setdefault(routed, []).append("routed")

    documents: list[dict[str, Any]] = []
    items = list(roles.items())
    truncated = len(items) > 30
    for relative, document_roles in items[:30]:
        try:
            content = read_bounded_text(
                root,
                relative,
                purpose="live Markdown document",
                required=False,
                max_lines=800,
            )
            metadata = file_metadata(root, relative)
            documents.append(
                {
                    **metadata,
                    "roles": document_roles,
                    "content": content,
                    "error": None,
                }
            )
        except InspectorError as exc:
            documents.append(
                {
                    "path": relative,
                    "exists": False,
                    "roles": document_roles,
                    "content": None,
                    "error": {"code": exc.code, "message": exc.message},
                }
            )
    return {
        "project_root": str(root),
        "read_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "documents": documents,
        "truncated": truncated,
    }
