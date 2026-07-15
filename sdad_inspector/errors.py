from __future__ import annotations

from typing import Any


class InspectorError(Exception):
    """A safe, user-presentable Inspector failure."""

    code = "inspection_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class PathSafetyError(InspectorError):
    code = "unsafe_path"


class BoundedReadError(InspectorError):
    code = "bounded_read_failed"


class UnsupportedContractError(InspectorError):
    code = "unsupported_contract"


class EngineError(InspectorError):
    code = "engine_error"


class DoctorOutputError(InspectorError):
    code = "invalid_doctor_output"


class ReportError(InspectorError):
    code = "report_error"


class PackageError(InspectorError):
    code = "package_error"


class InteractionError(InspectorError):
    code = "interaction_unavailable"
