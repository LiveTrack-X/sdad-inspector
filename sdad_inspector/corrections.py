"""App-owned correction drafts. No writes to inspected repositories."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from .errors import InspectorError

MAX_STORAGE_BYTES = 512 * 1024
MAX_ACTIVE_RECORDS = 40
PAGE_SIZE = 20
FIELDS = ("id", "request_id", "packet", "base_revision", "before", "correction", "supersedes", "copy_state")


class CorrectionError(InspectorError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def encoded_rows(rows):
    return json.dumps({"schema_version": 1, "drafts": rows}, ensure_ascii=False).encode("utf-8")


def check_capacity(rows):
    if len(rows) > MAX_ACTIVE_RECORDS:
        raise CorrectionError("Correction history is full (40). Archive saved records to free active capacity.", "correction_capacity")
    if len(encoded_rows(rows)) > MAX_STORAGE_BYTES:
        raise CorrectionError("Correction storage byte limit reached. Archive saved records to free active capacity.", "correction_capacity")


def validate_row(value):
    if not isinstance(value, dict) or any(not isinstance(value.get(k), str) or len(value[k]) > 4000 for k in (*FIELDS, "project_root")):
        raise CorrectionError("Invalid correction draft.", "correction_invalid")
    if any(not value[k].strip() for k in ("id", "project_root", "request_id", "packet", "base_revision")) or value["copy_state"] not in {"draft", "sealed", "copied"}:
        raise CorrectionError("Invalid correction identity or copy state.", "correction_invalid")
    if type(value.get("revision", 0)) is not int or value.get("revision", 0) < 0:
        raise CorrectionError("Invalid correction revision.", "correction_invalid")
    return {k: value[k] for k in (*FIELDS, "project_root")} | ({"revision": value["revision"]} if "revision" in value else {})


@contextmanager
def storage_lock(path: Path):
    """Serialize read-modify-replace across instances and app processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            deadline = time.monotonic() + 3
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise InspectorError("Correction storage is busy; retry the save.") from exc
                    time.sleep(0.025)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


class CorrectionStore:
    """Legacy JSON until explicit archiving; transactional storage thereafter.

    Activation preserves the exact legacy bytes and publishes a rejecting marker
    last. An old app cannot silently overwrite migrated saves. All instances use
    the same file lock, including reads during activation.
    """
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()

    @property
    def database_path(self):
        return self.path.with_name(self.path.name + ".sqlite3")

    @property
    def backup_path(self):
        return self.path.with_name(self.path.name + ".legacy.json")

    def _read(self):
        try:
            if self.path.stat().st_size > MAX_STORAGE_BYTES:
                raise ValueError("read limit")
            raw = self.path.read_bytes()
            value = json.loads(raw)
            if value.get("schema_version") == 2 and value.get("storage") == "sqlite" and isinstance(value.get("migration"), str) and len(value["migration"]) == 32:
                return value
            if value.get("schema_version") != 1 or not isinstance(value.get("drafts"), list):
                raise ValueError("schema")
            rows = value["drafts"]
            check_capacity(rows)
            for row in rows:
                validate_row(row)
            if len({r["id"] for r in rows}) != len(rows):
                raise ValueError("duplicate identity")
            return rows
        except FileNotFoundError:
            return []
        except (ValueError, AttributeError, OSError, InspectorError) as exc:
            raise CorrectionError("Correction storage is unreadable; existing data was preserved.", "correction_storage") from exc

    @contextmanager
    def _access(self):
        try:
            with self._lock, storage_lock(self.path):
                state = self._read()
                if isinstance(state, list):
                    yield state, None
                else:
                    if not self.database_path.is_file():
                        raise CorrectionError("Archived correction storage is missing; restore the app-data backup.", "correction_storage")
                    db = sqlite3.connect(self.database_path)
                    try:
                        marker = db.execute("SELECT substr(value,1,33) FROM metadata WHERE key='migration'").fetchone()
                        if marker != (state["migration"],):
                            raise CorrectionError("Correction storage identity does not match its marker.", "correction_storage")
                        rows = self._rows(db, archived=False)
                        check_capacity(rows)
                        yield rows, db
                    finally:
                        db.close()
        except (OSError, sqlite3.Error) as exc:
            raise CorrectionError("Correction storage is unavailable; existing data was preserved.", "correction_storage") from exc

    @staticmethod
    def _decode(body):
        try:
            if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_STORAGE_BYTES:
                raise ValueError("row limit")
            return validate_row(json.loads(body))
        except (ValueError, InspectorError) as exc:
            raise CorrectionError("Correction storage contains an unreadable record; existing data was preserved.", "correction_storage") from exc

    @staticmethod
    def _rows(db, *, archived, root=None, limit=MAX_ACTIVE_RECORDS + 1, offset=0):
        where = "archived=?" + (" AND project_root=?" if root is not None else "")
        params = [int(archived)] + ([root] if root is not None else []) + [limit, offset]
        bodies = db.execute(f"SELECT CASE WHEN length(CAST(body AS BLOB)) <= ? THEN body ELSE NULL END FROM corrections WHERE {where} ORDER BY sequence LIMIT ? OFFSET ?", [MAX_STORAGE_BYTES, *params]).fetchall()
        return [CorrectionStore._decode(body) for (body,) in bodies]

    def _replace_json(self, encoded):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + "." + uuid4().hex + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def _activate_archive(self, rows):
        # The legacy file remains authoritative until marker publication. An
        # interrupted unpublished database is replaced under the shared lock.
        migration = uuid4().hex
        temporary = self.database_path.with_name(self.database_path.name + "." + migration + ".tmp")
        try:
            with closing(sqlite3.connect(temporary)) as db, db:
                db.executescript("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE corrections(sequence INTEGER PRIMARY KEY,id TEXT UNIQUE,project_root TEXT,packet TEXT,request_id TEXT,supersedes TEXT,archived INTEGER,body TEXT); CREATE INDEX target ON corrections(project_root,packet,request_id); CREATE INDEX history ON corrections(archived,project_root,sequence);")
                db.execute("INSERT INTO metadata VALUES('migration',?)", (migration,))
                for row in rows:
                    self._put(db, row, False)
            original = self.path.read_bytes() if self.path.exists() else encoded_rows(rows)
            # Keep each failed activation's backup recoverable too.
            backup = self.backup_path if not self.backup_path.exists() else self.backup_path.with_name(self.backup_path.name + "." + migration)
            with backup.open("xb") as handle:
                handle.write(original)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.database_path)
            self._replace_json(json.dumps({"schema_version": 2, "storage": "sqlite", "migration": migration}).encode())
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _put(db, row, archived):
        db.execute("INSERT INTO corrections(id,project_root,packet,request_id,supersedes,archived,body) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET archived=excluded.archived,body=excluded.body", (row["id"], row["project_root"], row["packet"], row["request_id"], row["supersedes"], int(archived), json.dumps(row, ensure_ascii=False)))

    def load(self, root):
        with self._access() as (rows, _db):
            return [r for r in rows if r["project_root"] == root]

    def history(self, root, *, offset=0, archived=False, packet=None, request_id=None, page_size=PAGE_SIZE):
        if type(offset) is not int or not 0 <= offset <= 2147483647 or type(archived) is not bool or type(page_size) is not int or not 1 <= page_size <= MAX_ACTIVE_RECORDS:
            raise CorrectionError("Invalid history page.", "correction_invalid")
        with self._access() as (active, db):
            all_archived = db.execute("SELECT COUNT(*) FROM corrections WHERE archived=1").fetchone()[0] if db else 0
            project_archived = db.execute("SELECT COUNT(*) FROM corrections WHERE archived=1 AND project_root=?", (root,)).fetchone()[0] if db else 0
            rows = self._rows(db, archived=True, root=root, limit=page_size + 1, offset=offset) if archived and db else ([] if archived else [r for r in active if r["project_root"] == root][offset:offset + page_size + 1])
            leaf_id = None
            if isinstance(packet, str) and isinstance(request_id, str):
                if db:
                    leaves = db.execute("SELECT a.id FROM corrections a WHERE a.project_root=? AND a.packet=? AND a.request_id=? AND NOT EXISTS(SELECT 1 FROM corrections b WHERE b.project_root=a.project_root AND b.packet=a.packet AND b.request_id=a.request_id AND b.supersedes=a.id) LIMIT 2", (root, packet, request_id)).fetchall()
                    leaf_id = leaves[0][0] if len(leaves) == 1 else ""
                else:
                    target = [r for r in active if r["project_root"] == root and r["packet"] == packet and r["request_id"] == request_id]
                    replaced = {r["supersedes"] for r in target}
                    leaves = [r["id"] for r in target if r["id"] not in replaced]
                    leaf_id = leaves[0] if len(leaves) == 1 else ""
            return {"schema_version": 1, "project_root": root, "drafts": rows[:page_size], "has_more": len(rows) > page_size, "offset": offset, "archived": archived, "leaf_id": leaf_id, "usage": {"active_count": len(active), "active_limit": MAX_ACTIVE_RECORDS, "active_bytes": len(encoded_rows(active)), "byte_limit": MAX_STORAGE_BYTES, "archived_count": all_archived, "project_archived_count": project_archived}}

    def save(self, root, value):
        row = validate_row(value)
        if row["project_root"] != root:
            raise CorrectionError("Project changed; correction was not saved.", "correction_project")
        revision = row.pop("revision", 0)
        with self._access() as (rows, db):
            existing = next((r for r in rows if r["id"] == row["id"]), None)
            if not existing and db and db.execute("SELECT 1 FROM corrections WHERE id=?", (row["id"],)).fetchone():
                raise CorrectionError("This correction is archived. Restore it before editing.", "correction_archived")
            if existing and any(existing.get(k) != row[k] for k in ("project_root", "request_id", "packet", "base_revision", "supersedes")):
                raise CorrectionError("Correction ID already belongs to a different target.", "correction_conflict")
            if existing and all(existing.get(k) == v for k, v in row.items()):
                return existing
            if revision != (existing.get("revision", 0) if existing else 0):
                raise CorrectionError("Correction changed in another window. Your edit was not saved; create a new correction to preserve it.", "correction_conflict")
            if existing and existing["copy_state"] in {"sealed", "copied"}:
                changed = any(existing[k] != row[k] for k in FIELDS if k != "copy_state")
                allowed = row["copy_state"] == existing["copy_state"] or (existing["copy_state"] == "sealed" and row["copy_state"] == "copied")
                if changed or not allowed:
                    raise CorrectionError("A prepared or copied correction is immutable. Create a new correction.", "correction_conflict")
            row["revision"] = revision + 1
            rows = [row if r["id"] == row["id"] else r for r in rows] if existing else [*rows, row]
            check_capacity(rows)
            if db:
                self._put(db, row, False)
                db.commit()
            else:
                self._replace_json(encoded_rows(rows))
            return row

    def set_archived(self, root, value, archived):
        row = validate_row(value)
        if row["project_root"] != root:
            raise CorrectionError("Project changed; history was not changed.", "correction_project")
        with self._access() as (rows, db):
            existing = next((r for r in rows if r["id"] == row["id"]), None)
            if db:
                stored = db.execute("SELECT CASE WHEN length(CAST(body AS BLOB)) <= ? THEN body ELSE NULL END FROM corrections WHERE id=?", (MAX_STORAGE_BYTES, row["id"])).fetchone()
                existing = self._decode(stored[0]) if stored else None
            if existing != row:
                raise CorrectionError("Correction changed in another window. Refresh history before archiving or restoring.", "correction_conflict")
            if not archived:
                check_capacity(rows if any(r["id"] == row["id"] for r in rows) else [*rows, row])
            if db:
                self._put(db, row, archived)
                db.commit()
            elif archived:
                self._activate_archive(rows)
                # Activation is complete. Failure below leaves the record active,
                # so capacity and the original record remain unchanged.
                with closing(sqlite3.connect(self.database_path)) as archive_db, archive_db:
                    self._put(archive_db, row, True)
            return row

    def import_record(self, root, bundle):
        if not isinstance(bundle, dict) or bundle.get("schema_version") != 1 or bundle.get("kind") != "sdad-correction-export":
            raise CorrectionError("Invalid correction export.", "correction_invalid")
        row = validate_row(bundle.get("draft"))
        if row["project_root"] != root:
            raise CorrectionError("Export belongs to another project. Switch to that project before restoring.", "correction_project")
        with self._access() as (rows, db):
            existing = next((r for r in rows if r["id"] == row["id"]), None)
            if db:
                stored = db.execute("SELECT CASE WHEN length(CAST(body AS BLOB)) <= ? THEN body ELSE NULL END FROM corrections WHERE id=?", (MAX_STORAGE_BYTES, row["id"])).fetchone()
                existing = self._decode(stored[0]) if stored else None
            if existing is not None and existing != row:
                raise CorrectionError("An existing correction has different content. Import cannot replace it.", "correction_conflict")
            check_capacity(rows if any(r["id"] == row["id"] for r in rows) else [*rows, row])
            if db:
                self._put(db, row, False)
                db.commit()
            elif existing is None:
                self._replace_json(encoded_rows([*rows, row]))
            return row
