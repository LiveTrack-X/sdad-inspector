from __future__ import annotations
import json
import tempfile
import multiprocessing
import unittest
from pathlib import Path
from sdad_inspector.interactions import project_interactions
from sdad_inspector.corrections import CorrectionStore
from sdad_inspector.errors import InspectorError
from sdad_inspector.state import load_live_documents
from test_core import WorkspaceCase, tree_fingerprint


def record(kind="request", **values):
    return {"version": 1, "id": kind + "-1", "kind": kind, "packet": "P1", "request_id": "R1", "base_revision": "r1", "author": "agent", "reported_at": "2026-09-08T00:00:00Z", "summary": "Save settings", "source_ref": "SPEC/SPEC-COMPLETE.md#settings", **values}


def document(*records):
    return "<!-- sdad-interactions:1 -->\n" + "\n".join("```sdad-interaction\n" + json.dumps(r) + "\n```" for r in records)


def project(*records, **doc_values):
    return project_interactions([{"path": "docs/implementation-notes.md", "content": document(*records), **doc_values}], packet="P1", project_root="/project", read_at="now")


class ReportTests(unittest.TestCase):
    def test_current_stale_missing_and_wrong_packet_are_distinct(self):
        p = project(record(), record("interpretation"), record("response", id="old", base_revision="r0", correction_id="C1", stage="applied"), record("decision", packet="P2"), record("progress", request_id="unknown"))
        self.assertEqual([r["link_status"] for r in p["records"]], ["matched", "matched", "stale", "other_packet", "unresolved"])

    def test_corrected_requirement_revision_keeps_explicit_response_lineage(self):
        p = project(record(base_revision="r2"), record("response", correction_id="C1", stage="applied", result_revision="r2"))
        self.assertEqual(p["records"][1]["link_status"], "matched")
        p = project(record(base_revision="r3"), record("response", correction_id="C1", stage="applied", result_revision="r2"))
        self.assertEqual(p["records"][1]["link_status"], "stale")

    def test_malformed_kind_or_stage_never_crashes_reader(self):
        for bad in [{**record(), "kind": []}, record("response", correction_id="C1", stage={})]:
            self.assertEqual(project(bad)["status"], "incomplete")

    def test_duplicate_ids_and_competing_interpretations_are_conflicts(self):
        for values in [(record(), record()), (record(), record("interpretation"), record("interpretation", id="I2"))]:
            with self.subTest(values=values):
                self.assertIn("conflict", [r["link_status"] for r in project(*values)["records"]])

    def test_explicit_supersedes_replaces_interpretation_without_timestamp_sort(self):
        p = project(record(), record("interpretation", id="old"), record("interpretation", id="new", supersedes="old", reported_at="2020-01-01T00:00:00Z"))
        self.assertEqual([r["link_status"] for r in p["records"]], ["matched", "superseded", "matched"])

    def test_verification_command_without_result_does_not_parse_as_verification(self):
        p = project(record(), record("response", stage="verification_reported", correction_id="C1", command="pytest"))
        self.assertEqual(p["issues"][0]["code"], "verification_evidence_required")
        self.assertEqual(len(p["records"]), 1)

    def test_unsupported_version_and_truncated_reports_are_not_used(self):
        self.assertEqual(project(record(version=4))["status"], "incomplete")
        self.assertEqual(project(record(), truncated=True)["records"], [])

    def test_legacy_and_nested_examples_are_not_reports(self):
        for text in ["# Legacy", "````md\n" + document(record()) + "\n````"]:
            p = project_interactions([{"path":"x.md","content":text}], packet="P1", project_root="p", read_at="now")
            self.assertEqual(p["records"], [])

    def test_indented_outer_examples_are_ignored_and_longer_closers_resume(self):
        for indent in range(4):
            for fence in ("````", "~~~~"):
                with self.subTest(indent=indent, fence=fence):
                    content = ("<!-- sdad-interactions:1 -->\n" + " " * indent + fence + "markdown\n"
                               + document(record(id="example")) + "\n" + " " * indent
                               + fence + fence[0] + " \t\n" + document(record(id="actual")))
                    result = project_interactions([{"path": "notes.md", "content": content}],
                        packet="P1", project_root="/project", read_at="now")
                    self.assertEqual([r["id"] for r in result["records"]], ["actual"])
                    self.assertEqual(result["records"][0]["link_status"], "matched")

    def test_unknown_fields_do_not_override_observed_source(self):
        p = project(record(source={"path": "https://evil", "line": 0}, link_status="verified"))
        self.assertEqual(p["records"][0]["source"]["path"], "docs/implementation-notes.md")
        self.assertEqual(p["records"][0]["link_status"], "matched")


class ReadOnlyRoundTripTests(WorkspaceCase):
    def test_agent_report_roundtrip_uses_routed_authority_without_inspector_writes(self):
        # Simulate a user delivering a correction; only the agent writes the response.
        notes = self.project / "docs" / "implementation-notes.md"
        state = self.project / "sdad-state.yaml"
        state.write_text(state.read_text() + "\nrouted_docs:\n  - docs/implementation-notes.md\n", encoding="utf-8")
        packet = load_live_documents(self.project)["interactions"]["packet"]
        request = record(packet=packet)
        notes.write_text(document(request, record("interpretation", packet=packet)), encoding="utf-8")
        before = tree_fingerprint(self.project)
        result = load_live_documents(self.project)
        self.assertEqual(len(result["interactions"]["records"]), 2)
        self.assertEqual(tree_fingerprint(self.project), before)
        notes.write_text(document(request, record("response", packet=packet, correction_id="C1", stage="verification_reported", evidence=[{"path":"docs/implementation-notes.md", "result":"Executed cross-device test; passed"}])), encoding="utf-8")
        before = tree_fingerprint(self.project)
        result = load_live_documents(self.project)
        self.assertEqual(result["interactions"]["records"][1]["stage"], "verification_reported")
        self.assertEqual(tree_fingerprint(self.project), before)


class CorrectionTests(unittest.TestCase):
    def draft(self, **values):
        return {"id":"C1","project_root":"p1","request_id":"R1","packet":"P1","base_revision":"r1","before":"browser","correction":"account","supersedes":"","copy_state":"draft", **values}

    def test_stale_save_is_rejected_and_retry_preserves_history_order(self):
        with tempfile.TemporaryDirectory() as temp:
            store = CorrectionStore(Path(temp) / "corrections.json")
            first = store.save("p1", self.draft())
            store.save("p1", self.draft(id="C2"))
            fresh = store.save("p1", {**first, "correction":"latest"})
            with self.assertRaisesRegex(InspectorError, "another window"):
                store.save("p1", {**first, "correction":"stale"})
            self.assertEqual(store.save("p1", {**first, "correction":"latest"}), fresh)
            self.assertEqual([r["id"] for r in store.load("p1")], ["C1","C2"])
            self.assertEqual(store.load("p1")[0]["correction"], "latest")

    def test_legacy_draft_upgrades_on_edit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corrections.json"
            path.write_text(json.dumps({"schema_version":1,"drafts":[self.draft()]}))
            saved = CorrectionStore(path).save("p1", self.draft(correction="new"))
            self.assertEqual(saved["revision"], 1)

    def test_multibyte_limit_rejects_write_without_damaging_readable_store(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corrections.json"
            store = CorrectionStore(path)
            for i in range(40):
                previous = path.read_bytes() if path.exists() else b""
                try:
                    store.save("p1", self.draft(id=f"C{i}", before="가"*4000, correction="나"*4000))
                except InspectorError as exc:
                    self.assertIn("byte limit", str(exc))
                    self.assertEqual(path.read_bytes(), previous)
                    self.assertEqual(len(store.load("p1")), i)
                    break
            else:
                self.fail("The byte limit was not enforced")

    def test_processes_share_one_atomic_read_modify_write_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corrections.json"
            ctx = multiprocessing.get_context("spawn")
            start = ctx.Event()
            jobs = [ctx.Process(target=save_from_process, args=(str(path), start, prefix)) for prefix in ("a","b","c")]
            for job in jobs: job.start()
            start.set()
            for job in jobs:
                job.join(15)
                if job.is_alive(): job.terminate(); job.join()
                self.assertEqual(job.exitcode, 0)
            self.assertEqual(len(CorrectionStore(path).load("p1")), 30)

    def test_persistence_is_project_scoped_and_copied_requests_are_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "app" / "corrections.json"
            store = CorrectionStore(path)
            d = {"id":"C1","project_root":"p1","request_id":"R1","packet":"P1","base_revision":"r1","before":"browser","correction":"account","supersedes":"","copy_state":"copied"}
            d = store.save("p1", d)
            self.assertEqual(CorrectionStore(path).load("p1"), [d])
            self.assertEqual(store.load("p2"), [])
            with self.assertRaises(InspectorError): store.save("p2", d)
            with self.assertRaises(InspectorError): store.save("p1", {**d,"correction":"other"})
            prepared = {**d,"revision":0,"id":"C2","supersedes":"C1", "copy_state":"sealed"}
            prepared = store.save("p1", prepared)
            with self.assertRaises(InspectorError): store.save("p1", {**prepared,"correction":"different text"})
            store.save("p1", {**prepared,"copy_state":"copied"})
            self.assertEqual(len(store.load("p1")), 2)


def save_from_process(path, start, prefix):
    start.wait(5)
    for i in range(10):
        CorrectionStore(Path(path)).save("p1", CorrectionTests().draft(id=f"{prefix}{i}"))
