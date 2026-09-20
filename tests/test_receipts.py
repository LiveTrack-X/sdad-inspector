from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sdad_inspector.receipts import load_verification_receipts, validate_receipt, MAX_RECEIPTS
from test_core import WorkspaceCase, tree_fingerprint


def fixture_receipt():
    identity = {"size": 6, "sha256": hashlib.sha256(b"source").hexdigest()}
    return {"schema": "sdad.verification-receipt", "version": 1, "id": "fixture-1", "packet": "P1",
            "requirement": "R1", "scope": "fixture behavior", "cwd": ".",
            "command": {"argv": ["python", "-m", "unittest"], "platform": "Windows", "python_version": "3.12.0"},
            "started_at": "2026-09-20T00:00:00Z", "ended_at": "2026-09-20T00:00:01Z", "outcome": "passed", "exit_code": 0,
            "source_stability": "stable", "sources": [{"path": "source.py", "before": identity, "after": dict(identity), "error": None}],
            "log": {"path": "receipt.json.log", "sha256": hashlib.sha256(b"ok").hexdigest(), "bytes": 2, "total_bytes": 2, "truncated": False, "complete": True},
            "limits": ["Local unsigned observation; not semantic verification or owner acceptance."]}


class VerificationReceiptTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.receipt = fixture_receipt()
        (self.project / "source.py").write_bytes(b"source")
        (self.project / "receipt.json.log").write_bytes(b"ok")
        self.write_receipt()
        self.state = {"active_packet": {"id": "P2"}, "routed_docs": ["receipt.json"]}

    def write_receipt(self, value=None, name="receipt.json"):
        (self.project / name).write_text(json.dumps(self.receipt if value is None else value), encoding="utf-8")

    def read(self):
        return load_verification_receipts(self.project, state=self.state)

    def test_only_explicit_json_routes_read_without_command_execution_or_project_writes(self):
        before = tree_fingerprint(self.project)
        with patch("subprocess.Popen", side_effect=AssertionError("must not run")):
            result = self.read()
        self.assertEqual(before, tree_fingerprint(self.project))
        self.assertEqual(result["project_root"], str(self.project.resolve()))
        self.assertEqual(result["packet"], "P2")
        item = result["receipts"][0]
        self.assertEqual(item["receipt"]["packet"], "P1")
        self.assertEqual(item["source_match"], "matched")
        self.assertEqual(item["log_match"], "matched")
        self.state["routed_docs"] = []
        self.assertEqual(self.read()["receipts"], [])

    def test_current_source_and_log_tampering_are_independent(self):
        (self.project / "source.py").write_bytes(b"other!")
        item = self.read()["receipts"][0]
        self.assertEqual(item["source_match"], "changed")
        self.assertEqual(item["sources"][0]["reason"], "changed_since_run")
        self.assertEqual(item["log_match"], "matched")
        self.assertEqual(item["receipt"]["outcome"], "passed")
        (self.project / "receipt.json.log").write_bytes(b"no")
        self.assertEqual(self.read()["receipts"][0]["log_match"], "changed")

    def test_changed_during_run_never_becomes_matched_even_if_after_matches(self):
        self.receipt["sources"][0]["before"] = {"size": 3, "sha256": hashlib.sha256(b"old").hexdigest()}
        self.receipt["source_stability"] = "changed"
        self.write_receipt()
        item = self.read()["receipts"][0]
        self.assertEqual(item["source_match"], "changed")
        self.assertEqual(item["sources"][0]["reason"], "changed_during_run")

    def test_missing_source_or_log_is_unknown_not_matched(self):
        (self.project / "source.py").unlink()
        (self.project / "receipt.json.log").unlink()
        item = self.read()["receipts"][0]
        self.assertEqual((item["source_match"], item["log_match"]), ("unknown", "unknown"))

    def test_all_failed_outcomes_remain_visible(self):
        for outcome in ("failed", "timeout", "start_failed", "interrupted"):
            self.receipt.update(outcome=outcome, exit_code=7 if outcome == "failed" else None)
            self.write_receipt()
            item = self.read()["receipts"][0]
            self.assertEqual(item["receipt"]["outcome"], outcome)
            self.assertEqual(item["source_match"], "matched")

    def test_incomplete_and_truncated_logs_only_verify_retained_bytes(self):
        self.receipt["log"].update(total_bytes=1000, truncated=True, complete=False)
        self.write_receipt()
        item = self.read()["receipts"][0]
        self.assertEqual(item["log_match"], "matched")
        self.assertTrue(item["receipt"]["log"]["truncated"])
        self.assertFalse(item["receipt"]["log"]["complete"])

    def test_malformed_duplicate_fields_and_incomplete_capture_visible_as_diagnostic(self):
        for data in ('{"schema":"sdad.verification-receipt","version":1,"capture_incomplete":true}', '{"x":1,"x":2}', '[]', '{'):
            (self.project / "receipt.json").write_text(data)
            item = self.read()["receipts"][0]
            self.assertIsNone(item["receipt"])
            self.assertIsNotNone(item["error"])
            self.assertEqual(item["source_match"], "unknown")

    def test_strict_schema_outcomes_and_untrusted_paths_rejected(self):
        invalid = []
        for key, value in (("version", True), ("version", 2), ("outcome", "accepted"), ("exit_code", True), ("source_stability", "changed"), ("cwd", "../outside")):
            candidate = copy.deepcopy(self.receipt); candidate[key] = value; invalid.append(candidate)
        candidate = copy.deepcopy(self.receipt); candidate["log"]["path"] = "../outside"; invalid.append(candidate)
        candidate = copy.deepcopy(self.receipt); candidate["sources"][0]["path"] = ".env.local"; invalid.append(candidate)
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_receipt(candidate)

    def test_budget_and_missing_routes_expose_diagnostics_and_truncation(self):
        self.state["routed_docs"] = [f"missing-{i}.json" for i in range(MAX_RECEIPTS + 1)]
        result = self.read()
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["receipts"]), MAX_RECEIPTS)
        self.assertTrue(all(item["error"] for item in result["receipts"]))
        self.state["routed_docs"] = ["receipt.json"]
        with patch("sdad_inspector.receipts.MAX_TOTAL_SOURCE_BYTES", 2):
            self.assertEqual(self.read()["receipts"][0]["source_match"], "unknown")

    def test_path_traversal_and_output_overlap_cannot_be_evidence(self):
        self.state["routed_docs"] = ["../receipt.json", "C:/outside.json", ".git/config.json", ".GIT/config.json"]
        self.assertTrue(all(item["error"] for item in self.read()["receipts"]))
        self.state["routed_docs"] = ["receipt.json"]
        self.receipt["log"]["path"] = "source.py"
        self.write_receipt()
        self.assertIsNotNone(self.read()["receipts"][0]["error"])

    def test_symlink_cannot_supply_source_identity(self):
        (self.project / "source.py").unlink()
        outside = self.project.parent / "outside.py"; outside.write_bytes(b"source")
        try:
            (self.project / "source.py").symlink_to(outside)
        except OSError:
            self.skipTest("Symlink privilege unavailable")
        self.assertEqual(self.read()["receipts"][0]["source_match"], "unknown")

    def test_missing_observation_cannot_invent_stability(self):
        self.receipt["sources"][0].update(before=None, error="unreadable")
        self.receipt["source_stability"] = "unknown"
        self.write_receipt()
        item = self.read()["receipts"][0]
        self.assertEqual(item["source_match"], "unknown")
        self.assertEqual(item["receipt"]["source_stability"], "unknown")

    def test_windows_aliases_and_device_routes_rejected(self):
        self.state["routed_docs"] = ["CON.json", "NUL.json", "dir./receipt.json", "dir /receipt.json"]
        self.assertTrue(all(item["error"] for item in self.read()["receipts"]))


if __name__ == "__main__":
    unittest.main()
