"""App-owned correction drafts. No writes to inspected repositories."""
from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from .errors import InspectorError

MAX_STORAGE_BYTES = 512 * 1024


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
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()

    def _read(self) -> list[dict[str, Any]]:
        try:
            if self.path.stat().st_size > MAX_STORAGE_BYTES:
                raise InspectorError("Correction storage exceeds its read limit.")
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if value.get("schema_version") != 1 or not isinstance(value.get("drafts"), list) or len(value["drafts"]) > 40 or not all(isinstance(r, dict) and all(isinstance(r.get(k), str) for k in ("id", "project_root", "packet", "request_id", "base_revision", "before", "correction", "supersedes", "copy_state")) for r in value["drafts"]):
                raise ValueError()
            if any(type(r.get("revision", 0)) is not int or r.get("revision", 0) < 0 for r in value["drafts"]):
                raise ValueError()
            return value["drafts"]
        except FileNotFoundError:
            return []
        except (ValueError, AttributeError, OSError) as exc:
            raise InspectorError("Correction storage is unreadable; existing data was preserved.") from exc

    def load(self, root: str) -> list[dict[str, Any]]:
        with self._lock:
            return [r for r in self._read() if r.get("project_root") == root]

    def save(self, root: str, value: dict[str, Any]) -> dict[str, Any]:
        fields = ("id", "request_id", "packet", "base_revision", "before", "correction", "supersedes", "copy_state")
        if any(not isinstance(value.get(k), str) or len(value[k]) > 4000 for k in fields):
            raise InspectorError("Invalid correction draft.")
        if any(not value[k].strip() for k in ("id", "request_id", "packet", "base_revision")) or value["copy_state"] not in {"draft", "sealed", "copied"}:
            raise InspectorError("Invalid correction identity or copy state.")
        if value.get("project_root") != root:
            raise InspectorError("Project changed; correction was not saved.")
        row = {k: value[k] for k in fields}
        row["project_root"] = root
        revision = value.get("revision", 0)
        if type(revision) is not int or revision < 0:
            raise InspectorError("Invalid correction revision.")
        with self._lock, storage_lock(self.path):
            rows = self._read()
            existing = next((r for r in rows if r["id"] == row["id"]), None)
            if existing and any(existing.get(k) != row[k] for k in ("project_root", "request_id", "packet", "base_revision", "supersedes")):
                raise InspectorError("Correction ID already belongs to a different target.")
            if existing and all(existing.get(k) == v for k, v in row.items()):
                return existing  # Safe retry after a lost response; no history reorder.
            if revision != (existing.get("revision", 0) if existing else 0):
                raise InspectorError("Correction changed in another window. Your edit was not saved; create a new correction to preserve it.")
            if existing and existing.get("copy_state") in {"sealed", "copied"}:
                content_changed = any(existing.get(k) != row[k] for k in fields if k != "copy_state")
                allowed_state = row["copy_state"] == existing["copy_state"] or (existing["copy_state"] == "sealed" and row["copy_state"] == "copied")
                if content_changed or not allowed_state:
                    raise InspectorError("A prepared or copied correction is immutable. Create a new correction.")
            row["revision"] = revision + 1
            rows = [row if r["id"] == row["id"] else r for r in rows] if existing else [*rows, row]
            if len(rows) > 40:
                raise InspectorError("Correction history is full (40). Existing requests were preserved.")
            encoded = json.dumps({"schema_version": 1, "drafts": rows}, ensure_ascii=False).encode("utf-8")
            if len(encoded) > MAX_STORAGE_BYTES:
                raise InspectorError("Correction storage byte limit reached. Existing requests were preserved.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + "." + uuid4().hex + ".tmp")
            try:
                temporary.write_bytes(encoded)
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
            return row
