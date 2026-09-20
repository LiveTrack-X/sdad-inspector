import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from sdad_inspector.errors import InspectorError
from sdad_inspector.resume_store import MAX_PROJECTS, ResumeStore, observation


def snapshot(project="one", revision=1, **extra):
    return {
        "inspection_status": "completed", "inspection_id": str(revision),
        "inspected_at": f"2026-09-20T00:00:{revision:02d}Z", "project": {"root": f"/{project}", "identity": project},
        "integrity": {"control_files_unchanged_during_inspection": True}, "doctor": {"completed": True, "exit_code": 0},
        "protocol": {"state_path": "sdad-state.yaml", "todo_path": "docs/TODO.md", "findings_path": "review.md"},
        "state": {"available": True, "active_packet": {"id": "P1", "objective": f"Objective {revision}", "status": "deferred"},
            "active_spec": {"path": "SPEC.md"}, "current_handoff": {"declared": False}, "owner_gates": ["Local only"]},
        "evidence": {"files": {"SPEC.md": {"exists": True, "sha256": str(revision) * 64}}}, **extra,
    }


class ResumeStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name).resolve() / "app" / "resume.sqlite3"
        self.store = ResumeStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_opt_in_survives_new_store_instance_and_baseline_does_not_rotate(self):
        for action in ("read", "observe", "clear", "clear_all"):
            self.assertEqual(self.store.apply(snapshot(), action)["projects"], [])
            self.assertFalse(self.path.parent.exists())
        self.store.apply(snapshot(), "enable")
        reopened = ResumeStore(self.path)
        value = reopened.apply(snapshot(revision=2), "observe")["projects"][0]
        self.assertEqual(value["baseline"]["inspectionId"], "1")
        self.assertEqual(value["latest"]["inspectionId"], "2")
        self.assertEqual(value["latest"]["fields"]["status"]["text"], "deferred")
        self.assertEqual(reopened.apply(snapshot(revision=2), "enable")["projects"][0], value)
        self.assertEqual(reopened.apply(snapshot(revision=2), "replace")["projects"][0]["baseline"]["inspectionId"], "2")

    def test_failed_and_older_observations_do_not_replace_successful_history(self):
        self.store.apply(snapshot(revision=2), "enable")
        for status in ("stale", "diagnostic"):
            value = self.store.apply(snapshot(revision=3, inspection_status=status), "observe")
            self.assertEqual(value["projects"][0]["latest"]["inspectionId"], "2")
        self.assertEqual(self.store.apply(snapshot(revision=1), "observe")["projects"][0]["latest"]["inspectionId"], "2")
        with self.assertRaises(InspectorError): self.store.apply(snapshot(), "replace")
        with self.assertRaises(InspectorError): self.store.apply(snapshot(inspection_status="stale"), "enable")

    def test_project_isolation_clear_and_bounded_retention(self):
        self.store.apply(snapshot(), "enable")
        self.assertEqual(self.store.apply(snapshot("two"), "read")["projects"], [])
        for index in range(MAX_PROJECTS + 2): self.store.apply(snapshot(f"p{index}"), "enable")
        result = self.store.apply(snapshot("p9"), "read")
        self.assertEqual(result["retained_projects"], MAX_PROJECTS)
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(self.store.apply(snapshot(), "read")["projects"], [])
        self.assertEqual(self.store.apply(snapshot("p9"), "clear")["retained_projects"], MAX_PROJECTS - 1)
        self.assertEqual(self.store.apply(snapshot("p8"), "clear_all")["retained_projects"], 0)

    def test_invalid_stored_data_is_not_trusted_and_explicit_clear_recovers(self):
        self.store.apply(snapshot(), "enable")
        with closing(sqlite3.connect(self.path)) as db, db: db.execute("UPDATE resume_observations SET data='not JSON'")
        with self.assertRaises(InspectorError): self.store.apply(snapshot(), "read")
        self.assertEqual(self.store.apply(snapshot(), "clear")["projects"], [])
        self.assertTrue(self.store.apply(snapshot(), "enable")["projects"])

    def test_snapshots_are_bounded_and_do_not_store_source_bodies(self):
        value = snapshot()
        value["state"]["active_packet"]["objective"] = "x" * 1100
        value["evidence"]["files"]["SPEC.md"]["content"] = "do not retain"
        original = copy.deepcopy(value)
        item = observation(value)
        self.assertEqual(len(item["fields"]["objective"]["text"]), 1024)
        self.assertFalse(item["fields"]["objective"]["complete"])
        self.assertNotIn("do not retain", json.dumps(item))
        self.assertEqual(value, original)

    def test_concurrent_windows_merge_different_projects(self):
        self.store.apply(snapshot(), "enable")
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda name: ResumeStore(self.path).apply(snapshot(name), "enable"), ["a", "b", "c", "d"]))
        self.assertEqual(self.store.apply(snapshot(), "read")["retained_projects"], 5)

    def test_malformed_actions_are_controlled_errors(self):
        for action in ({}, [], None, "invalid"):
            with self.assertRaises(InspectorError): self.store.apply(snapshot(), action)

    def test_storage_cannot_write_inside_the_inspected_project(self):
        value = snapshot()
        value["project"]["root"] = self.temp.name
        for action in ("read", "observe", "enable", "clear_all"):
            with self.assertRaises(InspectorError): self.store.apply(value, action)
        self.assertFalse(self.path.exists())

    def test_diagnostic_doctor_is_not_a_completed_observation(self):
        for exit_code in (True, False, 0.0, "0", None):
            self.assertIsNone(observation(snapshot(doctor={"completed": True, "exit_code": exit_code})))
        self.assertIsNone(observation(snapshot(doctor={"completed": True, "exit_code": 2})))
        self.assertIsNone(observation(snapshot(doctor={"completed": True, "exit_code": 0, "diagnostic_error": {"kind": "bad"}})))

    def test_database_and_each_sidecar_hardlink_are_rejected_before_open(self):
        project = Path(self.temp.name).resolve() / "project"
        project.mkdir()
        target = project / "user-data"
        target.write_bytes(b"preserve project data")
        self.path.parent.mkdir()
        value = snapshot()
        value["project"] = {"root": str(project), "identity": "project"}
        for suffix in ("", "-journal", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            with self.subTest(suffix=suffix):
                os.link(target, candidate)
                try:
                    with patch("sdad_inspector.resume_store.sqlite3.connect") as connect:
                        for action in ("read", "enable", "clear_all"):
                            with self.assertRaises(InspectorError): self.store.apply(value, action)
                        connect.assert_not_called()
                    self.assertEqual(target.read_bytes(), b"preserve project data")
                    if suffix: self.assertFalse(self.path.exists())
                finally:
                    candidate.unlink()

    def test_sidecar_symlink_is_rejected_before_database_creation(self):
        self.path.parent.mkdir()
        target = Path(self.temp.name).resolve() / "project-data"
        target.write_bytes(b"preserve")
        sidecar = Path(str(self.path) + "-wal")
        try:
            sidecar.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaises(InspectorError): self.store.apply(snapshot(), "enable")
        self.assertFalse(self.path.exists())
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_parent_junction_or_reparse_point_is_rejected_before_creation(self):
        # lstat's Windows reparse flag covers junctions even on Python 3.10,
        # which has no Path.is_junction. Inject metadata without needing privilege.
        original_lstat = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == self.path.parent:
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return original_lstat(path, *args, **kwargs)
        with patch.object(Path, "lstat", lstat):
            with self.assertRaises(InspectorError): self.store.apply(snapshot(), "enable")
        self.assertFalse(self.path.parent.exists())

    def test_non_file_sidecar_is_rejected_before_database_creation(self):
        Path(str(self.path) + "-journal").mkdir(parents=True)
        with self.assertRaises(InspectorError): self.store.apply(snapshot(), "enable")
        self.assertFalse(self.path.exists())
