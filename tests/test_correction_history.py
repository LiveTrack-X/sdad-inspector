from __future__ import annotations
import json
from contextlib import closing
import multiprocessing
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from sdad_inspector.corrections import CorrectionError, CorrectionStore, MAX_STORAGE_BYTES
from sdad_inspector.errors import InspectorError


def draft(**values):
    return {"id":"C1", "project_root":"p1", "request_id":"R1", "packet":"P1", "base_revision":"r1", "before":"browser", "correction":"account", "supersedes":"", "copy_state":"draft", **values}


def concurrent_save(path, start, prefix):
    start.wait(5)
    store = CorrectionStore(Path(path))
    def retry_busy(operation):
        # A bounded busy response is allowed under contention. Exercise the
        # documented retry without hiding corruption, revision or other errors.
        deadline = time.monotonic() + 10
        while True:
            try:
                return operation()
            except InspectorError as exc:
                if exc.message != "Correction storage is busy; retry the save." or time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
    for index in range(8):
        row = retry_busy(lambda: store.save("p1", draft(id=f"{prefix}{index}")))
        retry_busy(lambda: store.set_archived("p1", row, True))


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "corrections.json"
        self.store = CorrectionStore(self.path)

    def assert_code(self, code, call):
        with self.assertRaises(CorrectionError) as raised:
            call()
        self.assertEqual(raised.exception.code, code)

    def test_full_active_history_recovers_capacity_and_preserves_global_ids(self):
        first = self.store.save("p1", draft())
        for n in range(1, 40):
            self.store.save("p2", draft(id=f"X{n}", project_root="p2"))
        usage = self.store.history("p1")["usage"]
        self.assertEqual(usage["active_count"], 40)
        self.assertEqual(len(self.store.history("p1")["drafts"]), 1)
        self.assert_code("correction_capacity", lambda: self.store.save("p1", draft(id="new")))
        original = self.path.read_bytes()
        self.store.set_archived("p1", first, True)
        self.assertEqual(self.store.backup_path.read_bytes(), original)
        self.assertEqual(json.loads(self.path.read_text())["schema_version"], 2)
        fresh = self.store.save("p1", draft(id="new", supersedes="C1"))
        self.assertEqual(self.store.history("p1", archived=True)["drafts"], [first])
        self.assertEqual(self.store.history("p1", packet="P1", request_id="R1")["leaf_id"], fresh["id"])
        self.assert_code("correction_archived", lambda: self.store.save("p2", draft(project_root="p2")))
        self.assert_code("correction_capacity", lambda: self.store.set_archived("p1", first, False))
        self.assertEqual(self.store.history("p1", archived=True)["drafts"], [first])
        self.store.set_archived("p1", fresh, True)
        self.store.set_archived("p1", first, False)
        self.assertEqual(self.store.load("p1"), [first])

    def test_archive_and_restore_keep_copy_state_revision_and_lineage(self):
        first = self.store.save("p1", draft(copy_state="copied"))
        second = self.store.save("p1", draft(id="C2", supersedes="C1", copy_state="sealed"))
        self.store.set_archived("p1", second, True)
        self.assertEqual(self.store.history("p1", packet="P1", request_id="R1")["leaf_id"], "C2")
        self.store.set_archived("p1", second, False)
        self.assertEqual(self.store.load("p1"), [first, second])
        self.assert_code("correction_conflict", lambda: self.store.save("p1", {**second, "correction":"changed"}))

    def test_stale_archive_and_import_never_overwrite_current_content(self):
        old = self.store.save("p1", draft())
        current = self.store.save("p1", {**old, "correction":"current"})
        self.assert_code("correction_conflict", lambda: self.store.set_archived("p1", old, True))
        self.assert_code("correction_conflict", lambda: self.store.import_record("p1", {"schema_version":1,"kind":"sdad-correction-export","draft":old}))
        self.assertEqual(self.store.load("p1"), [current])

    def test_export_import_roundtrip_and_project_boundary(self):
        row = self.store.save("p1", draft(before="가" * 4000, correction="나" * 4000, copy_state="copied"))
        bundle = {"schema_version":1,"kind":"sdad-correction-export","draft":row}
        other = CorrectionStore(Path(self.temp.name) / "other.json")
        self.assertEqual(other.import_record("p1", json.loads(json.dumps(bundle))), row)
        self.assertEqual(other.load("p1"), [row])
        self.assert_code("correction_project", lambda: other.import_record("p2", bundle))
        self.store.set_archived("p1", row, True)
        self.store.import_record("p1", bundle)
        self.assertEqual(self.store.load("p1"), [row])

    def test_archive_pages_are_bounded_and_all_records_recoverable(self):
        for n in range(47):
            row = self.store.save("p1", draft(id=f"C{n}", supersedes=f"C{n-1}" if n else ""))
            self.store.set_archived("p1", row, True)
        pages = [self.store.history("p1", archived=True, offset=n) for n in (0,20,40)]
        self.assertEqual([len(p["drafts"]) for p in pages], [20,20,7])
        self.assertEqual([p["has_more"] for p in pages], [True,True,False])
        self.assertEqual(len({r["id"] for p in pages for r in p["drafts"]}), 47)
        self.assertEqual(self.store.history("p1", packet="P1", request_id="R1")["leaf_id"], "C46")
        self.assertEqual(self.store.history("p2", archived=True)["drafts"], [])

    def test_marker_failure_leaves_legacy_authoritative_and_retry_keeps_new_saves(self):
        first = self.store.save("p1", draft())
        original = self.path.read_bytes()
        original_replace = os.replace
        def fail_marker(source, destination):
            if Path(destination) == self.path:
                raise OSError("marker unavailable")
            return original_replace(source, destination)
        with patch("sdad_inspector.corrections.os.replace", side_effect=fail_marker):
            self.assert_code("correction_storage", lambda: self.store.set_archived("p1", first, True))
        self.assertEqual(self.path.read_bytes(), original)
        current = self.store.save("p1", {**first, "correction":"saved after failure"})
        self.store.set_archived("p1", current, True)
        self.assertEqual(self.store.history("p1", archived=True)["drafts"], [current])
        self.assertEqual(self.store.backup_path.read_bytes(), original)

    def test_archive_transaction_failure_keeps_record_and_capacity_unchanged(self):
        first = self.store.save("p1", draft())
        self.store.set_archived("p1", first, True)
        self.store.set_archived("p1", first, False)
        original_put = CorrectionStore._put
        def fail_after_write(db, row, archived):
            original_put(db, row, archived)
            raise sqlite3.OperationalError("disk full")
        with patch.object(CorrectionStore, "_put", side_effect=fail_after_write):
            self.assert_code("correction_storage", lambda: self.store.set_archived("p1", first, True))
        self.assertEqual(self.store.load("p1"), [first])
        self.assertEqual(self.store.history("p1", archived=True)["drafts"], [])

    def test_invalid_exports_and_malformed_database_fail_without_replacement(self):
        for invalid in [None, {}, {"schema_version":1,"kind":"sdad-correction-export","draft":draft(correction="x" * 4001)}, {"schema_version":1,"kind":"sdad-correction-export","draft":draft(revision=True)}]:
            self.assert_code("correction_invalid", lambda: self.store.import_record("p1", invalid))
        row = self.store.save("p1", draft())
        self.store.set_archived("p1", row, True)
        with closing(sqlite3.connect(self.store.database_path)) as db, db:
            db.execute("UPDATE corrections SET body='{' WHERE id='C1'")
        self.assert_code("correction_storage", lambda: self.store.history("p1", archived=True))
        with closing(sqlite3.connect(self.store.database_path)) as db, db:
            self.assertEqual(db.execute("SELECT body FROM corrections WHERE id='C1'").fetchone(), ("{",))

    def test_oversized_database_record_is_rejected_by_bounded_read(self):
        row = self.store.save("p1", draft())
        self.store.set_archived("p1", row, True)
        with closing(sqlite3.connect(self.store.database_path)) as db, db:
            db.execute("UPDATE corrections SET body=? WHERE id='C1'", ("x" * (MAX_STORAGE_BYTES + 1),))
        self.assert_code("correction_storage", lambda: self.store.history("p1", archived=True))
        self.assert_code("correction_storage", lambda: self.store.set_archived("p1", row, False))

    def test_missing_database_does_not_recreate_or_downgrade(self):
        row = self.store.save("p1", draft())
        self.store.set_archived("p1", row, True)
        marker = self.path.read_bytes()
        self.store.database_path.unlink()
        self.assert_code("correction_storage", lambda: self.store.save("p1", draft(id="new")))
        self.assertFalse(self.store.database_path.exists())
        self.assertEqual(self.path.read_bytes(), marker)

    def test_multibyte_restoration_rechecks_same_active_byte_cap(self):
        archived = self.store.save("p1", draft(before="가" * 4000, correction="나" * 4000))
        self.store.set_archived("p1", archived, True)
        for n in range(40):
            try:
                self.store.save("p1", draft(id=f"X{n}", before="가" * 4000, correction="나" * 4000))
            except CorrectionError as exc:
                self.assertEqual(exc.code, "correction_capacity")
                break
        self.assert_code("correction_capacity", lambda: self.store.set_archived("p1", archived, False))
        self.assertLessEqual(self.store.history("p1")["usage"]["active_bytes"], MAX_STORAGE_BYTES)

    def test_processes_serialize_archive_and_save_without_lost_records(self):
        row = self.store.save("p1", draft())
        self.store.set_archived("p1", row, True)
        context = multiprocessing.get_context("spawn")
        start = context.Event()
        jobs = [context.Process(target=concurrent_save, args=(str(self.path), start, prefix)) for prefix in ("A", "B", "D")]
        for job in jobs: job.start()
        start.set()
        for job in jobs:
            job.join(20)
            if job.is_alive(): job.terminate(); job.join()
            self.assertEqual(job.exitcode, 0)
        self.assertEqual(self.store.history("p1")["usage"]["archived_count"], 25)
        self.assertEqual(self.store.load("p1"), [])
