from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import DoctorOutputError, UnsupportedContractError

SUPPORTED_REPORT_SCHEMAS = (1, 2)


def _integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DoctorOutputError(f"Doctor field {field} must be a non-negative integer.")
    return value


def _string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DoctorOutputError(f"Doctor field {field} must be a string list.")
    return list(value)


def _normalize_finding(value: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DoctorOutputError(f"Doctor finding {index} must be an object.")
    required = ("id", "severity", "path", "message", "evidence", "remediation")
    if any(not isinstance(value.get(key), str) for key in required):
        raise DoctorOutputError(f"Doctor finding {index} has invalid required fields.")
    line = value.get("line")
    if line is not None and (isinstance(line, bool) or not isinstance(line, int) or line < 1):
        raise DoctorOutputError(f"Doctor finding {index} has an invalid line.")
    return {
        "id": value["id"],
        "severity": value["severity"],
        "path": value["path"],
        "line": line,
        "message": value["message"],
        "evidence": value["evidence"],
        "remediation": value["remediation"],
    }


def adapt_doctor_report(
    report: dict[str, Any],
    *,
    engine_version: str,
    expected_root: Path | None,
) -> dict[str, Any]:
    schema = report.get("schema_version")
    if schema not in SUPPORTED_REPORT_SCHEMAS:
        raise UnsupportedContractError(
            "This Doctor report schema is not supported.",
            details={"observed": schema, "supported": list(SUPPORTED_REPORT_SCHEMAS)},
        )
    if schema == 2 and report.get("doctor_version") != engine_version:
        raise DoctorOutputError(
            "Doctor report version does not match the probed engine.",
            details={
                "report": report.get("doctor_version"),
                "engine": engine_version,
            },
        )
    state_version = report.get("state_version") if schema == 2 else None
    if state_version not in {None, 1, 2}:
        raise UnsupportedContractError(
            "This state schema is not supported.",
            details={"observed": state_version, "supported": [1, 2]},
        )

    report_root = report.get("root")
    if report_root is not None and not isinstance(report_root, str):
        raise DoctorOutputError("Doctor field root must be a string or null.")
    if expected_root is not None and report_root is not None:
        try:
            observed_root = Path(report_root).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise DoctorOutputError("Doctor returned an invalid project root.") from exc
        if observed_root != expected_root:
            raise DoctorOutputError(
                "Doctor inspected a different project root.",
                details={"observed": report_root, "expected": str(expected_root)},
            )

    summary = report.get("summary")
    checks = report.get("checks")
    findings = report.get("findings")
    if not isinstance(summary, dict) or not isinstance(checks, dict) or not isinstance(findings, list):
        raise DoctorOutputError("Doctor report is missing summary, checks, or findings.")
    diagnostic = report.get("diagnostic_error")
    if diagnostic is not None:
        if not isinstance(diagnostic, dict) or not all(
            isinstance(diagnostic.get(key), str) for key in ("kind", "message")
        ):
            raise DoctorOutputError("Doctor diagnostic_error is malformed.")
        normalized_diagnostic: dict[str, str] | None = {
            "kind": diagnostic["kind"],
            "message": diagnostic["message"],
        }
    else:
        normalized_diagnostic = None

    return {
        "report_schema_version": schema,
        "doctor_version": engine_version,
        "state_schema_version": state_version,
        "root": report_root,
        "strict": bool(report.get("strict")),
        "summary": {
            "errors": _integer(summary.get("errors"), field="summary.errors"),
            "warnings": _integer(summary.get("warnings"), field="summary.warnings"),
        },
        "checks": {
            "run": _string_list(checks.get("run"), field="checks.run"),
            "skipped": _string_list(checks.get("skipped"), field="checks.skipped"),
        },
        "findings": [
            _normalize_finding(finding, index=index)
            for index, finding in enumerate(findings)
        ],
        "diagnostic_error": normalized_diagnostic,
    }
