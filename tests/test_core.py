from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sdad_inspector.adapters import adapt_doctor_report
from sdad_inspector.engine import (
    RELEASE_COMMITS,
    RELEASE_TREE_SHA256,
    EngineInfo,
    _release_tree_digest,
    probe_engine,
)
from sdad_inspector.errors import (
    DoctorOutputError,
    EngineError,
    PathSafetyError,
    UnsupportedContractError,
)
from sdad_inspector.paths import read_bounded_text, safe_project_path
from sdad_inspector.snapshot import inspect_project

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "sdad"

FAKE_ENGINE = r'''from __future__ import annotations
import json
import sys
from pathlib import Path

if sys.argv[1:] == ["--version"]:
    print("3.2.2")
    raise SystemExit(0)

engine_root = Path(__file__).resolve().parents[1]
mode_file = engine_root / "mode.txt"
mode = mode_file.read_text(encoding="utf-8").strip() if mode_file.exists() else "ok"
if mode == "malformed":
    print('{"schema_version": 2,')
    raise SystemExit(0)

project = str(Path(sys.argv[2]).resolve())
state_version = 1 if mode == "state1" else 2
report = {
    "schema_version": 2,
    "doctor_version": "3.2.1" if mode == "version-mismatch" else "3.2.2",
    "state_version": state_version,
    "root": project,
    "strict": "--strict" in sys.argv,
    "summary": {"errors": 0, "warnings": 0},
    "checks": {"run": ["state_schema"], "skipped": []},
    "findings": [],
}
exit_code = 0
if mode == "finding":
    report["summary"]["errors"] = 1
    report["findings"] = [{
        "id": "state.missing", "severity": "error", "path": "sdad-state.yaml",
        "line": None, "message": "Missing state", "evidence": "missing",
        "remediation": "Create state"
    }]
    exit_code = 1
elif mode == "diagnostic":
    report["root"] = None
    report["state_version"] = None
    report["diagnostic_error"] = {"kind": "invalid_root", "message": "Invalid root"}
    exit_code = 2
print(json.dumps(report))
raise SystemExit(exit_code)
'''


def tree_fingerprint(root: Path) -> dict[str, tuple[int, int, str]]:
    result: dict[str, tuple[int, int, str]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        stat = path.stat()
        result[path.relative_to(root).as_posix()] = (
            stat.st_size,
            stat.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return result


class WorkspaceCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sdad-inspector-")
        self.root = Path(self.temporary.name)
        self.engine = self.root / "engine"
        (self.engine / "scripts").mkdir(parents=True)
        (self.engine / "scripts" / "sdad.py").write_text(FAKE_ENGINE, encoding="utf-8")
        (self.engine / ".sdad-release.json").write_text(
            json.dumps(
                {
                    "doctor_version": "3.2.2",
                    "release_tag": "v3.2.2",
                    "peeled_commit": RELEASE_COMMITS["3.2.2"],
                    "source": "fixture",
                }
            ),
            encoding="utf-8",
        )
        self.engine_info = EngineInfo(
            checkout=str(self.engine.resolve()),
            doctor_version="3.2.2",
            release_tag="v3.2.2",
            revision=RELEASE_COMMITS["3.2.2"],
            source="fixture",
            trust="test-injection",
            clean=True,
        )
        self.project = self.root / "프로젝트 with spaces"
        (self.project / "SPEC").mkdir(parents=True)
        (self.project / "docs").mkdir()
        (self.project / "SPEC" / "SPEC-COMPLETE.md").write_text(
            "# Fixture SPEC\n", encoding="utf-8"
        )
        (self.project / "docs" / "TODO-Open-Items.md").write_text(
            "# Open Implementation Items\n\n## Active Work\n\n"
            "- [ ] [packet:CORE-1] Do not execute the validation command.\n",
            encoding="utf-8",
        )
        (self.project / "review-findings.md").write_text(
            "# Review Findings\n\n## Active Findings\n\nNone currently tracked.\n",
            encoding="utf-8",
        )
        self.write_state()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_state(
        self,
        *,
        version: int = 2,
        active_spec: str = "SPEC/SPEC-COMPLETE.md",
        handoff: str | None = None,
    ) -> None:
        lines = [
            f"version: {version}",
            "updated: 2026-07-15",
            "scale: standard",
        ]
        if version == 2:
            lines.append("execution_scope: packet")
        else:
            lines.extend(["intensity: low", "autonomy: 2"])
        lines.extend(
            [
                f"active_spec: {active_spec}",
                "active_packet:",
                "  id: CORE-1",
                "  objective: Prove the read-only core.",
                "  status: in_progress",
            ]
        )
        if version == 2:
            lines.append("validation_for: CORE-1")
        if handoff:
            lines.append(f"current_handoff: {handoff}")
        lines.extend(
            [
                "owner_gates:",
                "  - release",
                "  - auto-fix/write",
                "validation:",
                "  - command: python VALIDATION_MUST_NOT_RUN.py",
                "    proves: This command is metadata only.",
                "routed_docs:",
                "  - docs/TODO-Open-Items.md",
                "  - review-findings.md",
            ]
        )
        (self.project / "sdad-state.yaml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )


class AdapterTests(unittest.TestCase):
    def test_all_frozen_reports_normalize_without_erasing_the_raw_contract(self) -> None:
        for version in ("v3.2.1", "v3.2.2"):
            for path in sorted((FIXTURES / version).glob("*.json")):
                with self.subTest(version=version, fixture=path.name):
                    report = json.loads(path.read_text(encoding="utf-8"))
                    normalized = adapt_doctor_report(
                        report, engine_version=version[1:], expected_root=None
                    )
                    self.assertIn(normalized["report_schema_version"], {1, 2})
                    self.assertEqual(
                        normalized["summary"]["errors"], report["summary"]["errors"]
                    )

    def test_unknown_report_schema_fails_closed(self) -> None:
        with self.assertRaises(UnsupportedContractError):
            adapt_doctor_report(
                {"schema_version": 99}, engine_version="3.2.2", expected_root=None
            )


class CoreInspectionTests(WorkspaceCase):
    def test_snapshot_is_read_only_and_never_executes_declared_validation(self) -> None:
        before = tree_fingerprint(self.project)
        snapshot = inspect_project(self.project, self.engine, _engine_info=self.engine_info)
        after = tree_fingerprint(self.project)
        self.assertEqual(before, after)
        self.assertFalse((self.project / "VALIDATION_MUST_NOT_RUN.py").exists())
        self.assertTrue(snapshot["read_only"])
        self.assertTrue(
            snapshot["integrity"]["control_files_unchanged_during_inspection"]
        )
        self.assertTrue(all(not item["executed"] for item in snapshot["state"]["validation"]))

    def test_inspection_emits_observed_pipeline_progress_without_percentages(self) -> None:
        events: list[tuple[str, str, str]] = []
        snapshot = inspect_project(
            self.project,
            self.engine,
            _engine_info=self.engine_info,
            progress_callback=lambda stage, source, event: events.append(
                (stage, source, event)
            ),
        )

        self.assertEqual(snapshot["doctor"]["exit_code"], 0)
        self.assertEqual(events[0][0], "prepare")
        self.assertIn(("doctor", "scripts/sdad.py", "doctor_started"), events)
        self.assertTrue(
            any(
                stage == "controls" and source == "sdad-state.yaml"
                for stage, source, _ in events
            )
        )
        self.assertEqual(events[-1][0], "report")
        self.assertNotIn("percent", json.dumps(events))

    def test_snapshot_preserves_raw_report_exit_code_and_unicode_path(self) -> None:
        (self.engine / "mode.txt").write_text("finding", encoding="utf-8")
        snapshot = inspect_project(self.project, self.engine, _engine_info=self.engine_info)
        self.assertEqual(snapshot["doctor"]["exit_code"], 1)
        self.assertEqual(snapshot["evidence"]["doctor_exit_code"], 1)
        self.assertEqual(snapshot["evidence"]["doctor_report"]["summary"]["errors"], 1)
        self.assertIn("프로젝트 with spaces", snapshot["project"]["root"])

    def test_exit_two_is_a_diagnostic_not_a_completed_inspection(self) -> None:
        (self.engine / "mode.txt").write_text("diagnostic", encoding="utf-8")
        snapshot = inspect_project(self.project, self.engine, _engine_info=self.engine_info)
        self.assertEqual(snapshot["inspection_status"], "diagnostic")
        self.assertFalse(snapshot["doctor"]["completed"])
        self.assertEqual(snapshot["doctor"]["diagnostic_error"]["kind"], "invalid_root")

    def test_handoff_present_and_absent_are_explicit(self) -> None:
        handoff = "docs/sdad/handoffs/2026-07-15-H0001-core.md"
        (self.project / "docs" / "sdad" / "handoffs").mkdir(parents=True)
        (self.project / handoff).write_text("# Handoff\n", encoding="utf-8")
        self.write_state(handoff=handoff)
        present = inspect_project(self.project, self.engine, _engine_info=self.engine_info)
        self.assertTrue(present["state"]["current_handoff"]["exists"])
        (self.project / handoff).unlink()
        absent = inspect_project(self.project, self.engine, _engine_info=self.engine_info)
        self.assertFalse(absent["state"]["current_handoff"]["exists"])

    def test_state_v1_is_normalized_without_inventing_validation_for(self) -> None:
        self.write_state(version=1)
        (self.engine / "mode.txt").write_text("state1", encoding="utf-8")
        snapshot = inspect_project(self.project, self.engine, _engine_info=self.engine_info)
        self.assertEqual(snapshot["state"]["schema_version"], 1)
        self.assertIsNone(snapshot["state"]["validation_for"])
        self.assertEqual(snapshot["state"]["legacy_controls"]["autonomy"], 2)

    def test_unknown_state_version_fails_closed(self) -> None:
        self.write_state(version=99)
        with self.assertRaises(UnsupportedContractError):
            inspect_project(self.project, self.engine, _engine_info=self.engine_info)

    def test_malformed_doctor_json_is_rejected(self) -> None:
        (self.engine / "mode.txt").write_text("malformed", encoding="utf-8")
        with self.assertRaises(DoctorOutputError):
            inspect_project(self.project, self.engine, _engine_info=self.engine_info)

    def test_report_engine_version_mismatch_is_rejected(self) -> None:
        (self.engine / "mode.txt").write_text("version-mismatch", encoding="utf-8")
        with self.assertRaises(DoctorOutputError):
            inspect_project(self.project, self.engine, _engine_info=self.engine_info)

    def test_active_spec_path_traversal_is_rejected(self) -> None:
        self.write_state(active_spec="../outside.md")
        with self.assertRaises(PathSafetyError):
            inspect_project(self.project, self.engine, _engine_info=self.engine_info)

    def test_project_root_alias_is_canonicalized_before_containment(self) -> None:
        active_spec = safe_project_path(
            self.project,
            "SPEC/SPEC-COMPLETE.md",
            purpose="active SPEC",
            must_exist=True,
        )
        self.assertEqual(active_spec, (self.project / "SPEC/SPEC-COMPLETE.md").resolve())

    def test_symlink_control_file_is_rejected(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("secret\n", encoding="utf-8")
        link = self.project / "SPEC" / "LINK.md"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("symbolic links are not available in this environment")
        self.write_state(active_spec="SPEC/LINK.md")
        with self.assertRaises(PathSafetyError):
            inspect_project(self.project, self.engine, _engine_info=self.engine_info)

    def test_hard_link_control_file_is_rejected(self) -> None:
        outside = self.root / "outside-hardlink.md"
        outside.write_text("secret\n", encoding="utf-8")
        link = self.project / "SPEC" / "HARDLINK.md"
        try:
            os.link(outside, link)
        except OSError:
            self.skipTest("hard links are not available in this environment")
        self.write_state(active_spec="SPEC/HARDLINK.md")
        with self.assertRaises(PathSafetyError):
            inspect_project(self.project, self.engine, _engine_info=self.engine_info)

    def test_bounded_read_rejects_large_control_text(self) -> None:
        large = self.project / "docs" / "large.md"
        large.write_text("x" * 1024, encoding="utf-8")
        with self.assertRaises(Exception):
            read_bounded_text(
                self.project,
                "docs/large.md",
                purpose="large fixture",
                required=True,
                max_bytes=32,
            )


class EngineTrustTests(WorkspaceCase):
    def test_release_archive_tree_is_authenticated_before_execution(self) -> None:
        observed = _release_tree_digest(self.engine)
        with patch.dict(RELEASE_TREE_SHA256, {"3.2.2": observed}):
            engine = probe_engine(self.engine)
        self.assertEqual(engine.trust, "release-marker")
        self.assertEqual(engine.revision, RELEASE_COMMITS["3.2.2"])

    def test_release_marker_must_match_frozen_commit(self) -> None:
        marker = json.loads((self.engine / ".sdad-release.json").read_text(encoding="utf-8"))
        marker["peeled_commit"] = "0" * 40
        (self.engine / ".sdad-release.json").write_text(
            json.dumps(marker), encoding="utf-8"
        )
        with self.assertRaises(EngineError):
            probe_engine(self.engine)

    def test_unsupported_doctor_version_is_rejected_before_inspection(self) -> None:
        script = self.engine / "scripts" / "sdad.py"
        script.write_text(
            'import sys\nprint("9.9.9")\n', encoding="utf-8"
        )
        marker = json.loads((self.engine / ".sdad-release.json").read_text(encoding="utf-8"))
        marker["doctor_version"] = "9.9.9"
        marker["release_tag"] = "v9.9.9"
        (self.engine / ".sdad-release.json").write_text(
            json.dumps(marker), encoding="utf-8"
        )
        with self.assertRaises(UnsupportedContractError):
            probe_engine(self.engine)


if __name__ == "__main__":
    unittest.main()
