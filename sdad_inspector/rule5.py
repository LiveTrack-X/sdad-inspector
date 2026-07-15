from __future__ import annotations

import hashlib
import os
import re
import secrets
from pathlib import Path
from typing import Any, Mapping

from .errors import InspectorError, PathSafetyError
from .paths import read_bounded_text

RULE5_SOURCE_PATH = "review-findings.md"
MAX_RULE5_FIELD_CHARS = 4000
MAX_RULE5_EXPORT_BYTES = 48 * 1024
UNKNOWN = "Unknown - owner review required."


class Rule5Error(InspectorError):
    code = "rule5_invalid"


_FIELD_LABELS = {
    "root cause": "root_cause",
    "근본 원인": "root_cause",
    "control": "operational_rule",
    "operational rule": "operational_rule",
    "rule": "operational_rule",
    "제어": "operational_rule",
    "규칙": "operational_rule",
    "trigger": "trigger",
    "트리거": "trigger",
    "non-trigger": "non_trigger",
    "non trigger": "non_trigger",
    "비트리거": "non_trigger",
    "exceptions": "exceptions",
    "exception": "exceptions",
    "예외": "exceptions",
    "enforcement": "enforcement",
    "강제": "enforcement",
    "regression evidence": "regression_evidence",
    "regression": "regression_evidence",
    "회귀 근거": "regression_evidence",
    "limits": "limits",
    "limitations": "limits",
    "한계": "limits",
    "review condition": "review_condition",
    "review": "review_condition",
    "검토 조건": "review_condition",
}


def _active_findings(markdown: str) -> list[tuple[str, str, dict[str, str]]]:
    lines = markdown.splitlines()
    inside = False
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    active_field: str | None = None
    for line in lines:
        if re.match(r"^##\s+Active Findings\s*$", line, re.IGNORECASE):
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if not inside:
            continue
        match = re.match(
            r"^- (?:\[(?:Critical|High|Medium|Low)\] )?"
            r"\[packet:[^\]]+\] \[([A-Za-z0-9._-]+)\]\s*(.*)$",
            line,
        )
        if match is None:
            # Preserve bounded support for older pre-v2 finding records while
            # preferring the current SDAD 3.2.2 ledger grammar above.
            match = re.match(r"^- \[([A-Za-z0-9._-]+)\]\s*(.*)$", line)
        if match:
            current = {"id": match.group(1), "failure": [match.group(2).strip()], "fields": {}}
            records.append(current)
            active_field = None
            continue
        if current is None or not line.strip():
            continue
        labeled = re.match(r"^\s{2,}(?:-\s*)?([^:：]{2,40})[:：]\s*(.*)$", line)
        if labeled:
            key = _FIELD_LABELS.get(labeled.group(1).strip().casefold())
            if key:
                current["fields"][key] = labeled.group(2).strip()
                active_field = key
                continue
        if re.match(r"^\s{2,}\S", line):
            text = line.strip()
            if active_field:
                current["fields"][active_field] = f'{current["fields"][active_field]} {text}'.strip()
            else:
                current["failure"].append(text)

    result: list[tuple[str, str, dict[str, str]]] = []
    for record in records:
        finding_id = str(record["id"])
        if not finding_id.upper().startswith("FIND-"):
            continue
        failure = " ".join(str(item) for item in record["failure"] if item).strip()
        failure = re.sub(r"^(?:\[[^\]]+\]\s*)+", "", failure)
        if failure:
            result.append((finding_id, failure, dict(record["fields"])))
    return result


def extract_rule5_candidates(project_root: Path) -> dict[str, Any]:
    markdown = read_bounded_text(
        project_root,
        RULE5_SOURCE_PATH,
        purpose="Rule 5 finding source",
        required=False,
    ) or ""
    source_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    candidates: list[dict[str, Any]] = []
    for finding_id, failure, fields in _active_findings(markdown):
        candidate_id = f"R5-{finding_id}"
        candidate = {
            "candidate_id": candidate_id,
            "finding_id": finding_id,
            "source_path": RULE5_SOURCE_PATH,
            "source_sha256": source_sha256,
            "observed_failure": failure,
            "root_cause": fields.get("root_cause", ""),
            "operational_rule": fields.get("operational_rule", ""),
            "trigger": fields.get("trigger", f"Repeated recurrence or one high-risk missing control recorded by {finding_id}."),
            "non_trigger": fields.get("non_trigger", "A one-off preference or a failure already prevented by an effective control."),
            "exceptions": fields.get("exceptions", ""),
            "enforcement": fields.get("enforcement", ""),
            "regression_evidence": fields.get("regression_evidence", ""),
            "limits": fields.get("limits", ""),
            "review_condition": fields.get("review_condition", "Keep, Refine, Merge, or Retire after field use."),
        }
        candidate["complete"] = all(
            candidate[field]
            for field in (
                "observed_failure",
                "root_cause",
                "operational_rule",
                "enforcement",
                "regression_evidence",
                "review_condition",
            )
        )
        candidates.append(candidate)
    return {
        "source_path": RULE5_SOURCE_PATH,
        "source_sha256": source_sha256,
        "candidates": candidates[:40],
    }


def _field(payload: Mapping[str, object], name: str, *, required: bool = False) -> str:
    value = payload.get(name)
    if not isinstance(value, str):
        if required:
            raise Rule5Error(f"Rule 5 field '{name}' is required.")
        return ""
    value = value.strip()
    if len(value) > MAX_RULE5_FIELD_CHARS:
        raise Rule5Error(f"Rule 5 field '{name}' exceeds its bounded size.")
    if required and not value:
        raise Rule5Error(f"Rule 5 field '{name}' is required.")
    return value


def build_rule5_proposal(payload: Mapping[str, object]) -> dict[str, str]:
    candidate_id = _field(payload, "candidate_id", required=True)
    if not re.fullmatch(r"R5-[A-Za-z0-9._-]{1,100}", candidate_id):
        raise Rule5Error("Rule 5 candidate ID is invalid.")
    finding_id = _field(payload, "finding_id", required=True)
    source_path = _field(payload, "source_path", required=True)
    source_sha256 = _field(payload, "source_sha256", required=True)
    if source_path != RULE5_SOURCE_PATH or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise Rule5Error("Rule 5 source identity is invalid.")
    values = {
        "observed_failure": _field(payload, "observed_failure", required=True),
        "root_cause": _field(payload, "root_cause", required=True),
        "operational_rule": _field(payload, "operational_rule", required=True),
        "trigger": _field(payload, "trigger") or UNKNOWN,
        "non_trigger": _field(payload, "non_trigger") or UNKNOWN,
        "exceptions": _field(payload, "exceptions") or UNKNOWN,
        "enforcement": _field(payload, "enforcement", required=True),
        "regression_evidence": _field(payload, "regression_evidence", required=True),
        "limits": _field(payload, "limits") or UNKNOWN,
        "review_condition": _field(payload, "review_condition", required=True),
    }
    markdown = (
        f"# Rule 5 Proposal: {candidate_id}\n\n"
        "Status: Candidate - not an active rule or owner acceptance\n\n"
        "Revision: 1\n\n"
        "## Origin / Lineage\n\n"
        f"- Finding: `{finding_id}`\n"
        f"- Source: `{source_path}`\n"
        f"- Source SHA-256: `{source_sha256}`\n\n"
        "## Observed Failure\n\n"
        f"{values['observed_failure']}\n\n"
        "## Root Cause\n\n"
        f"{values['root_cause']}\n\n"
        "## Trigger\n\n"
        f"{values['trigger']}\n\n"
        "## Non-Trigger\n\n"
        f"{values['non_trigger']}\n\n"
        "## Operational Rule\n\n"
        f"{values['operational_rule']}\n\n"
        "## Exceptions\n\n"
        f"{values['exceptions']}\n\n"
        "## Enforcement\n\n"
        f"{values['enforcement']}\n\n"
        "## Regression Evidence\n\n"
        f"{values['regression_evidence']}\n\n"
        "## Limits\n\n"
        f"{values['limits']}\n\n"
        "## Owner Decision\n\n"
        "Not decided. Exporting this proposal does not adopt it.\n\n"
        "## Keep / Refine / Merge / Retire Condition\n\n"
        f"{values['review_condition']}\n"
    )
    encoded = markdown.encode("utf-8")
    if len(encoded) > MAX_RULE5_EXPORT_BYTES:
        raise Rule5Error("The Rule 5 proposal exceeds its bounded export size.")
    return {
        "markdown": markdown,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "suggested_filename": f"{candidate_id}.md",
    }


def write_rule5_export(
    destination: str | Path,
    markdown: str,
    *,
    forbidden_root: str | Path | None = None,
) -> Path:
    encoded = markdown.encode("utf-8")
    if not encoded or len(encoded) > MAX_RULE5_EXPORT_BYTES:
        raise Rule5Error("The Rule 5 export content is empty or oversized.")
    target = Path(destination).expanduser()
    if target.suffix.casefold() != ".md":
        target = target.with_suffix(".md")
    try:
        parent = target.parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathSafetyError("The selected export directory is unavailable.") from exc
    if not parent.is_dir() or target.name in {"", ".", ".."} or "\x00" in target.name:
        raise PathSafetyError("The selected Rule 5 export path is invalid.")
    target = parent / target.name
    if forbidden_root is not None:
        root = Path(forbidden_root).resolve(strict=True)
        if target == root or target.is_relative_to(root):
            raise PathSafetyError(
                "Rule 5 proposals must be saved outside the inspected repository."
            )
    if target.exists() and (target.is_dir() or target.is_symlink()):
        raise PathSafetyError("The selected Rule 5 export target is unsafe.")
    temporary = parent / f".{target.name}.{secrets.token_hex(6)}.tmp"
    try:
        try:
            with temporary.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except OSError as exc:
            raise Rule5Error("The Rule 5 proposal could not be written to the selected path.") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return target
