from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from sdad_inspector.engine import DoctorRun, EngineInfo
from sdad_inspector.errors import UnsupportedContractError
from sdad_inspector.protocols import (
    DEFAULT_PROTOCOL_ADAPTER_ID,
    ProtocolAdapter,
    ProtocolDescriptor,
    registered_protocol_adapters,
    resolve_protocol_adapter,
)
from sdad_inspector.server import InspectorService
from sdad_inspector.snapshot import inspect_project


class FixtureAdapter(ProtocolAdapter):
    descriptor = ProtocolDescriptor(
        adapter_id="fixture-sdad",
        protocol_name="Fixture SDAD",
        engine_name="Fixture Engine",
        doctor_entrypoint="tools/check.py",
        state_path="control.json",
        todo_path="work/TODO.md",
        findings_path="work/FINDINGS.md",
        supported_engine_versions=("9.1",),
        supported_report_schemas=(7,),
        supported_state_schemas=(4,),
        normalized_control_loop=("Plan", "Route", "Implement", "Verify", "Report"),
        capabilities=("doctor", "control-state", "live-documents"),
    )

    def probe_engine(self, checkout: str | Path, *, timeout: float) -> EngineInfo:
        del timeout
        return EngineInfo(
            checkout=str(Path(checkout).resolve()),
            doctor_version="9.1",
            release_tag="fixture-9.1",
            revision="fixture-revision",
            source="fixture",
            trust="test-injection",
            clean=True,
        )

    def run_doctor(
        self,
        engine: EngineInfo,
        project_root: Path,
        *,
        timeout: float,
        strict: bool,
    ) -> DoctorRun:
        del timeout
        return DoctorRun(
            exit_code=0,
            argv_shape=["fixture", "check", "<PROJECT_ROOT>"],
            report={
                "schema_version": 7,
                "root": str(project_root),
                "strict": strict,
            },
            stderr_present=False,
        )

    def adapt_doctor_report(
        self,
        report: dict[str, Any],
        *,
        engine_version: str,
        expected_root: Path | None,
    ) -> dict[str, Any]:
        return {
            "report_schema_version": report["schema_version"],
            "doctor_version": engine_version,
            "state_schema_version": 4,
            "root": str(expected_root) if expected_root is not None else None,
            "strict": bool(report.get("strict")),
            "summary": {"errors": 0, "warnings": 0},
            "checks": {"run": ["fixture"], "skipped": []},
            "findings": [],
            "diagnostic_error": None,
        }

    def peek_control_paths(self, root: Path) -> list[str]:
        del root
        return [self.descriptor.state_path]

    def load_control_state(
        self,
        root: Path,
        *,
        observer=None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, object]]]:
        if observer is not None:
            observer(self.descriptor.state_path)
        return (
            {
                "available": True,
                "schema_version": 4,
                "active_spec": None,
                "active_packet": None,
                "validation_for": None,
                "validation": [],
                "owner_gates": [],
                "routed_docs": [],
                "current_handoff": None,
                "ledger": {
                    "todo_open": 0,
                    "review_findings_open": 0,
                    "review_findings_by_severity": {},
                },
            },
            {
                self.descriptor.state_path: {
                    "path": self.descriptor.state_path,
                    "exists": (root / self.descriptor.state_path).is_file(),
                }
            },
        )

    def load_live_documents(self, root: Path) -> dict[str, Any]:
        return {"project_root": str(root), "documents": [], "truncated": False}


class ProtocolAdapterTests(unittest.TestCase):
    def test_default_adapter_is_explicit_and_version_bounded(self) -> None:
        adapter = resolve_protocol_adapter()
        self.assertEqual(adapter.descriptor.adapter_id, DEFAULT_PROTOCOL_ADAPTER_ID)
        self.assertEqual(adapter.descriptor.supported_engine_versions, ("3.2.1", "3.2.2"))
        self.assertIn(
            DEFAULT_PROTOCOL_ADAPTER_ID,
            {descriptor.adapter_id for descriptor in registered_protocol_adapters()},
        )

    def test_unknown_adapter_fails_closed_without_project_discovery(self) -> None:
        with self.assertRaises(UnsupportedContractError):
            resolve_protocol_adapter("project-supplied-adapter")

    def test_explicit_adapter_drives_engine_state_and_snapshot_metadata(self) -> None:
        adapter = FixtureAdapter()
        with tempfile.TemporaryDirectory(prefix="sdad-adapter-") as raw:
            root = Path(raw)
            project = root / "project"
            engine = root / "engine"
            project.mkdir()
            engine.mkdir()
            (project / "control.json").write_text("{}\n", encoding="utf-8")

            snapshot = inspect_project(
                project,
                engine,
                protocol_adapter=adapter,
            )

        self.assertEqual(snapshot["snapshot_schema_version"], 2)
        self.assertEqual(snapshot["protocol"]["adapter_id"], "fixture-sdad")
        self.assertEqual(snapshot["protocol"]["engine_display_name"], "Fixture Engine 9.1")
        self.assertEqual(snapshot["contracts"]["report_schema_version"], 7)
        self.assertEqual(snapshot["contracts"]["state_schema_version"], 4)
        self.assertEqual(snapshot["integrity"]["watched_control_paths"], ["control.json"])
        self.assertTrue(snapshot["integrity"]["control_files_unchanged_during_inspection"])

    def test_desktop_service_reuses_the_selected_adapter_for_live_surfaces(self) -> None:
        adapter = FixtureAdapter()
        with tempfile.TemporaryDirectory(prefix="sdad-adapter-service-") as raw:
            root = Path(raw)
            project = root / "project"
            engine = root / "engine"
            project.mkdir()
            engine.mkdir()
            (project / "control.json").write_text("{}\n", encoding="utf-8")

            service = InspectorService(
                project,
                engine,
                protocol_adapter=adapter,
            )

            self.assertEqual(service.snapshot()["protocol"]["adapter_id"], "fixture-sdad")
            self.assertEqual(service.documents()["project_root"], str(project.resolve()))


if __name__ == "__main__":
    unittest.main()
