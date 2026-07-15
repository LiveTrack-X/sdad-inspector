from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeAlias

from .activity import load_development_activity as _load_development_activity
from .adapters import SUPPORTED_REPORT_SCHEMAS, adapt_doctor_report
from .engine import (
    SUPPORTED_DOCTOR_VERSIONS,
    DoctorRun,
    EngineInfo,
    probe_engine as _probe_engine,
    run_doctor as _run_doctor,
)
from .errors import UnsupportedContractError
from .rule5 import (
    build_rule5_proposal as _build_rule5_proposal,
    extract_rule5_candidates as _extract_rule5_candidates,
)
from .state import (
    SUPPORTED_STATE_SCHEMAS,
    ReadObserver,
    load_control_state as _load_control_state,
    load_live_documents as _load_live_documents,
    peek_control_paths as _peek_control_paths,
)

DEFAULT_PROTOCOL_ADAPTER_ID = "official-sdad-3"


@dataclass(frozen=True)
class ProtocolDescriptor:
    """Stable metadata exposed by one explicitly installed SDAD adapter."""

    adapter_id: str
    protocol_name: str
    engine_name: str
    doctor_entrypoint: str
    state_path: str
    todo_path: str
    findings_path: str
    supported_engine_versions: tuple[str, ...]
    supported_report_schemas: tuple[int, ...]
    supported_state_schemas: tuple[int, ...]
    normalized_control_loop: tuple[str, ...]
    capabilities: tuple[str, ...]

    def to_snapshot(self, *, engine_version: str) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "protocol_name": self.protocol_name,
            "engine_name": self.engine_name,
            "engine_display_name": f"{self.engine_name} {engine_version}",
            "doctor_entrypoint": self.doctor_entrypoint,
            "state_path": self.state_path,
            "todo_path": self.todo_path,
            "findings_path": self.findings_path,
            "supported_engine_versions": list(self.supported_engine_versions),
            "supported_report_schemas": list(self.supported_report_schemas),
            "supported_state_schemas": list(self.supported_state_schemas),
            "normalized_control_loop": list(self.normalized_control_loop),
            "capabilities": list(self.capabilities),
        }


class ProtocolAdapter(ABC):
    """Explicit trust boundary between Inspector orchestration and SDAD rules.

    Adapters are installed and registered by the operator or product build. An
    inspected repository is data only and can never select or load Python code.
    """

    descriptor: ProtocolDescriptor

    def validate_engine(self, engine: EngineInfo) -> None:
        supported = self.descriptor.supported_engine_versions
        if engine.doctor_version not in supported:
            raise UnsupportedContractError(
                "The selected protocol adapter does not support this engine.",
                details={
                    "adapter_id": self.descriptor.adapter_id,
                    "observed": engine.doctor_version,
                    "supported": list(supported),
                },
            )

    @abstractmethod
    def probe_engine(self, checkout: str | Path, *, timeout: float) -> EngineInfo:
        raise NotImplementedError

    @abstractmethod
    def run_doctor(
        self,
        engine: EngineInfo,
        project_root: Path,
        *,
        timeout: float,
        strict: bool,
    ) -> DoctorRun:
        raise NotImplementedError

    @abstractmethod
    def adapt_doctor_report(
        self,
        report: dict[str, Any],
        *,
        engine_version: str,
        expected_root: Path | None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def peek_control_paths(self, root: Path) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def load_control_state(
        self,
        root: Path,
        *,
        observer: ReadObserver | None = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, object]]]:
        raise NotImplementedError

    @abstractmethod
    def load_live_documents(self, root: Path) -> dict[str, Any]:
        raise NotImplementedError

    def load_development_activity(self, root: Path) -> dict[str, Any]:
        return _load_development_activity(root, state_loader=self.load_control_state)

    def extract_rule5_candidates(self, root: Path) -> dict[str, Any]:
        raise UnsupportedContractError(
            "The selected protocol adapter does not provide Rule 5 surfaces.",
            details={"adapter_id": self.descriptor.adapter_id},
        )

    def build_rule5_proposal(self, payload: dict[str, Any]) -> dict[str, str]:
        raise UnsupportedContractError(
            "The selected protocol adapter does not provide Rule 5 surfaces.",
            details={"adapter_id": self.descriptor.adapter_id},
        )


class OfficialSdad3Adapter(ProtocolAdapter):
    descriptor = ProtocolDescriptor(
        adapter_id=DEFAULT_PROTOCOL_ADAPTER_ID,
        protocol_name="Official SDAD Protocol",
        engine_name="SDAD",
        doctor_entrypoint="scripts/sdad.py",
        state_path="sdad-state.yaml",
        todo_path="docs/TODO-Open-Items.md",
        findings_path="review-findings.md",
        supported_engine_versions=tuple(SUPPORTED_DOCTOR_VERSIONS),
        supported_report_schemas=tuple(SUPPORTED_REPORT_SCHEMAS),
        supported_state_schemas=tuple(SUPPORTED_STATE_SCHEMAS),
        normalized_control_loop=("Plan", "Route", "Implement", "Verify", "Report"),
        capabilities=(
            "doctor",
            "control-state",
            "live-documents",
            "development-activity",
            "rule5-proposals",
        ),
    )

    def probe_engine(self, checkout: str | Path, *, timeout: float) -> EngineInfo:
        engine = _probe_engine(checkout, timeout=timeout)
        self.validate_engine(engine)
        return engine

    def run_doctor(
        self,
        engine: EngineInfo,
        project_root: Path,
        *,
        timeout: float,
        strict: bool,
    ) -> DoctorRun:
        self.validate_engine(engine)
        return _run_doctor(engine, project_root, timeout=timeout, strict=strict)

    def adapt_doctor_report(
        self,
        report: dict[str, Any],
        *,
        engine_version: str,
        expected_root: Path | None,
    ) -> dict[str, Any]:
        return adapt_doctor_report(
            report,
            engine_version=engine_version,
            expected_root=expected_root,
        )

    def peek_control_paths(self, root: Path) -> list[str]:
        return _peek_control_paths(root)

    def load_control_state(
        self,
        root: Path,
        *,
        observer: ReadObserver | None = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, object]]]:
        return _load_control_state(root, observer=observer)

    def load_live_documents(self, root: Path) -> dict[str, Any]:
        return _load_live_documents(root)

    def extract_rule5_candidates(self, root: Path) -> dict[str, Any]:
        return _extract_rule5_candidates(root)

    def build_rule5_proposal(self, payload: dict[str, Any]) -> dict[str, str]:
        return _build_rule5_proposal(payload)


ProtocolAdapterReference: TypeAlias = str | ProtocolAdapter | None
_ADAPTERS: dict[str, ProtocolAdapter] = {}


def register_protocol_adapter(
    adapter: ProtocolAdapter,
    *,
    replace: bool = False,
) -> None:
    """Register already-imported operator code; never discover code in a project."""

    if not isinstance(adapter, ProtocolAdapter):
        raise TypeError("Protocol adapters must inherit ProtocolAdapter.")
    adapter_id = adapter.descriptor.adapter_id
    if not adapter_id or any(character.isspace() for character in adapter_id):
        raise ValueError("Protocol adapter IDs must be non-empty and contain no spaces.")
    if adapter_id in _ADAPTERS and not replace:
        raise ValueError(f"Protocol adapter {adapter_id!r} is already registered.")
    _ADAPTERS[adapter_id] = adapter


def registered_protocol_adapters() -> tuple[ProtocolDescriptor, ...]:
    return tuple(_ADAPTERS[key].descriptor for key in sorted(_ADAPTERS))


def resolve_protocol_adapter(
    reference: ProtocolAdapterReference = None,
) -> ProtocolAdapter:
    if isinstance(reference, ProtocolAdapter):
        return reference
    adapter_id = reference or DEFAULT_PROTOCOL_ADAPTER_ID
    adapter = _ADAPTERS.get(adapter_id)
    if adapter is None:
        raise UnsupportedContractError(
            "The requested protocol adapter is not installed.",
            details={
                "requested": adapter_id,
                "installed": sorted(_ADAPTERS),
            },
        )
    return adapter


register_protocol_adapter(OfficialSdad3Adapter())
