"""Bounded app-owned resume observations, independent of browser ports.

Only completed Inspector snapshots enter this store. Its contents never control
project execution, acceptance, or permission. SQLite serializes multiple windows.
"""
from __future__ import annotations

from datetime import datetime
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import stat
from typing import Any

from .errors import InspectorError

MAX_PROJECTS = 8
MAX_BYTES = 192 * 1024
FIELDS = ("packet", "objective", "status", "gates", "spec", "handoff")
SHA = re.compile(r"^[a-fA-F0-9]{64}$")


def _guard_storage_paths(path: Path, project_root: Path) -> None:
    """Check SQLite's database and sidecars before opening or creating anything.

    Reject aliases rather than trusting SQLite to follow them safely. This is a
    local path guard, not protection from a process racing filesystem changes.
    """
    try:
        for suffix in ("", "-journal", "-wal", "-shm"):
            candidate = Path(str(path) + suffix).absolute()
            if candidate.resolve().is_relative_to(project_root):
                raise ValueError("Storage is inside the inspected project")
            for component in (candidate, *candidate.parents):
                try:
                    info = component.lstat()
                except FileNotFoundError:
                    continue
                if (stat.S_ISLNK(info.st_mode)
                        or getattr(info, "st_file_attributes", 0) & 0x400):
                    raise ValueError("Storage path contains a link or reparse point")
                if component == candidate:
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise ValueError("Storage file is not a single-link regular file")
                elif not stat.S_ISDIR(info.st_mode):
                    raise ValueError("Storage parent is not a directory")
    except (OSError, RuntimeError, ValueError) as exc:
        raise InspectorError("Resume storage must be outside the inspected project and use ordinary, unlinked files and directories. Project files were not changed.") from exc


def _bounded(value: str | None) -> dict:
    return {"text": value[:1024] if value is not None else None,
            "complete": value is None or len(value) <= 1024}


def observation(snapshot: dict) -> dict | None:
    state = snapshot.get("state", {})
    if (snapshot.get("inspection_status") != "completed" or not state.get("available")
            or snapshot.get("integrity", {}).get("control_files_unchanged_during_inspection") is not True
            or snapshot.get("doctor", {}).get("completed") is not True
            or snapshot.get("doctor", {}).get("diagnostic_error") is not None
            or type(snapshot.get("doctor", {}).get("exit_code")) is not int
            or snapshot.get("doctor", {}).get("exit_code") not in (0, 1)):
        return None
    packet = state.get("active_packet") or {}
    spec = (state.get("active_spec") or {}).get("path")
    handoff = state.get("current_handoff") or {}
    handoff_path = handoff.get("path") if handoff.get("declared") else None
    protocol = snapshot["protocol"]
    files = snapshot.get("evidence", {}).get("files", {})
    paths = sorted(set(p for p in [protocol["state_path"], spec, protocol["todo_path"],
        protocol["findings_path"], handoff_path, *files] if isinstance(p, str) and p))
    eligible = [p for p in paths if len(p) <= 1024]
    sources = []
    for path in eligible[:32]:
        metadata = files.get(path) or {}
        exists = metadata.get("exists") if type(metadata.get("exists")) is bool else None
        digest = metadata.get("sha256")
        sources.append({"path": path, "exists": exists, "sha256": digest.lower()
            if exists is True and isinstance(digest, str) and SHA.fullmatch(digest) else None})
    return {
        "projectIdentity": snapshot["project"]["identity"], "projectRoot": snapshot["project"]["root"],
        "inspectionId": snapshot["inspection_id"], "inspectedAt": snapshot["inspected_at"],
        "statePath": protocol["state_path"],
        "fields": {"packet": _bounded(packet.get("id")), "objective": _bounded(packet.get("objective")),
            "status": _bounded(packet.get("status")), "gates": _bounded("\n".join(state.get("owner_gates") or [])),
            "spec": _bounded(spec), "handoff": _bounded(handoff_path)},
        "sources": sources, "sourcesOmitted": len(paths) != len(eligible) or len(eligible) > 32,
    }


def _date(value: str) -> datetime:
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Unzoned time")
    return date


def _validate_entry(entry: Any) -> dict:
    if not isinstance(entry, dict) or set(entry) != {"baseline", "latest"}:
        raise ValueError("Invalid observation pair")
    for item in entry.values():
        if not isinstance(item, dict) or set(item) != {"projectIdentity", "projectRoot", "inspectionId", "inspectedAt", "statePath", "fields", "sources", "sourcesOmitted"}:
            raise ValueError("Invalid observation")
        for key in ("projectIdentity", "projectRoot", "inspectionId", "inspectedAt", "statePath"):
            if not isinstance(item[key], str) or not 0 < len(item[key]) <= (2048 if key == "projectRoot" else 1024):
                raise ValueError("Invalid observation identity")
        _date(item["inspectedAt"])
        if type(item["sourcesOmitted"]) is not bool or not isinstance(item["fields"], dict) or set(item["fields"]) != set(FIELDS):
            raise ValueError("Invalid observation fields")
        for field in item["fields"].values():
            if (not isinstance(field, dict) or set(field) != {"text", "complete"}
                    or type(field["complete"]) is not bool
                    or not (field["text"] is None or isinstance(field["text"], str) and len(field["text"]) <= 1024)):
                raise ValueError("Invalid bounded value")
        if not isinstance(item["sources"], list) or len(item["sources"]) > 32:
            raise ValueError("Invalid source identities")
        for source in item["sources"]:
            if (not isinstance(source, dict) or set(source) != {"path", "exists", "sha256"}
                    or not isinstance(source["path"], str) or not 0 < len(source["path"]) <= 1024
                    or not (source["exists"] is None or type(source["exists"]) is bool)
                    or not (source["sha256"] is None or isinstance(source["sha256"], str) and SHA.fullmatch(source["sha256"]))):
                raise ValueError("Invalid source identity")
    a, b = entry["baseline"], entry["latest"]
    if (a["projectIdentity"], a["projectRoot"]) != (b["projectIdentity"], b["projectRoot"]) or _date(a["inspectedAt"]) > _date(b["inspectedAt"]):
        raise ValueError("Mismatched observation pair")
    return entry


class ResumeStore:
    def __init__(self, path: Path):
        self.path = path

    def apply(self, snapshot: dict, action: str) -> dict:
        if not isinstance(action, str) or action not in {"read", "enable", "observe", "replace", "clear", "clear_all"}:
            raise InspectorError("Unknown resume comparison action.")
        project_root = Path(snapshot["project"]["root"]).resolve()
        _guard_storage_paths(self.path, project_root)
        key = json.dumps([snapshot["project"]["identity"], snapshot["project"]["root"]])
        if not self.path.exists() and action in {"read", "observe", "clear", "clear_all"}:
            return {"version": 1, "projects": [], "retained_projects": 0}
        current = observation(snapshot)
        if action in {"enable", "replace"} and current is None:
            raise InspectorError("Only a completed, coherent inspection can be saved.")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _guard_storage_paths(self.path, project_root)
            with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
                db.execute("PRAGMA journal_size_limit=262144")
                db.execute("CREATE TABLE IF NOT EXISTS resume_observations (project TEXT PRIMARY KEY, data TEXT NOT NULL, touched INTEGER NOT NULL)")
                db.execute("BEGIN IMMEDIATE")
                if action == "clear_all":
                    db.execute("DELETE FROM resume_observations")
                elif action == "clear":
                    db.execute("DELETE FROM resume_observations WHERE project=?", (key,))
                size_row = db.execute("SELECT length(CAST(data AS BLOB)) FROM resume_observations WHERE project=?", (key,)).fetchone()
                if size_row and size_row[0] > MAX_BYTES:
                    raise ValueError("Stored record exceeds budget")
                row = db.execute("SELECT data FROM resume_observations WHERE project=?", (key,)).fetchone()
                existing = None
                if row:
                    if len(row[0].encode("utf-8")) > MAX_BYTES:
                        raise ValueError("Stored record exceeds budget")
                    existing = _validate_entry(json.loads(row[0]))
                    if [existing["baseline"]["projectIdentity"], existing["baseline"]["projectRoot"]] != [snapshot["project"]["identity"], snapshot["project"]["root"]]:
                        raise ValueError("Stored project mismatch")
                if action in {"enable", "observe", "replace"} and current and (existing or action != "observe"):
                    if existing and _date(current["inspectedAt"]) < _date(existing["latest"]["inspectedAt"]):
                        if action == "replace":
                            raise InspectorError("A newer observation exists; refresh before replacing the baseline.")
                    else:
                        entry = _validate_entry({"baseline": current if not existing or action == "replace" else existing["baseline"], "latest": current})
                        encoded = json.dumps(entry, ensure_ascii=False)
                        if len(encoded.encode("utf-8")) > MAX_BYTES:
                            raise ValueError("Observation exceeds storage budget")
                        if existing != entry:
                            serial = db.execute("SELECT COALESCE(MAX(touched),0)+1 FROM resume_observations").fetchone()[0]
                            db.execute("INSERT OR REPLACE INTO resume_observations VALUES (?,?,?)", (key, encoded, serial))
                # Retain the most recently changed projects and bound serialized data.
                rows = db.execute("SELECT project, length(CAST(data AS BLOB)) FROM resume_observations ORDER BY touched DESC, project").fetchall()
                used = 0
                for index, (project, size) in enumerate(rows):
                    used += size
                    if index >= MAX_PROJECTS or used > MAX_BYTES:
                        db.execute("DELETE FROM resume_observations WHERE project=?", (project,))
                result = db.execute("SELECT data FROM resume_observations WHERE project=?", (key,)).fetchone()
                count = db.execute("SELECT COUNT(*) FROM resume_observations").fetchone()[0]
                return {"version": 1, "projects": [_validate_entry(json.loads(result[0]))] if result else [], "retained_projects": count}
        except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            raise InspectorError("Resume history is unavailable or invalid. Clear its records to reset it; current project files are unchanged.") from exc
