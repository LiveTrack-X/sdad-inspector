from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

PREFERENCES_SCHEMA_VERSION = 1
MAX_RECENT_PROJECTS = 6
MAX_PREFERENCES_BYTES = 64 * 1024
MAX_PATH_CHARS = 4096
MAX_NAME_CHARS = 255


def default_preferences_path(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    platform = platform or sys.platform
    environ = environ or os.environ
    home = home or Path.home()
    if platform == "win32":
        base = Path(environ.get("LOCALAPPDATA") or (home / "AppData" / "Local"))
        return base / "SDAD Inspector" / "preferences.json"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "SDAD Inspector" / "preferences.json"
    base = Path(environ.get("XDG_CONFIG_HOME") or (home / ".config"))
    return base / "sdad-inspector" / "preferences.json"


def _validated_records(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, dict) or payload.get("schema_version") != PREFERENCES_SCHEMA_VERSION:
        return []
    records = payload.get("recent_projects")
    if not isinstance(records, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        name = item.get("name")
        opened_at = item.get("opened_at")
        if not (
            isinstance(path, str)
            and 0 < len(path) <= MAX_PATH_CHARS
            and isinstance(name, str)
            and 0 < len(name) <= MAX_NAME_CHARS
            and isinstance(opened_at, str)
            and 0 < len(opened_at) <= 64
        ):
            continue
        key = os.path.normcase(path)
        if key in seen:
            continue
        seen.add(key)
        result.append({"path": path, "name": name, "opened_at": opened_at})
        if len(result) >= MAX_RECENT_PROJECTS:
            break
    return result


class RecentProjectsStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_preferences_path()
        self._lock = threading.RLock()

    def load(self) -> list[dict[str, str]]:
        with self._lock:
            try:
                if not self.path.is_file() or self.path.stat().st_size > MAX_PREFERENCES_BYTES:
                    return []
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                return []
            return _validated_records(payload)

    def remember(self, projects: Iterable[tuple[str | Path, str]]) -> list[dict[str, str]]:
        with self._lock:
            records = self.load()
            opened_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            for project_path, project_name in projects:
                path = str(project_path)
                name = str(project_name)
                if not path or len(path) > MAX_PATH_CHARS or not name or len(name) > MAX_NAME_CHARS:
                    continue
                key = os.path.normcase(path)
                records = [item for item in records if os.path.normcase(item["path"]) != key]
                records.insert(0, {"path": path, "name": name, "opened_at": opened_at})
            records = records[:MAX_RECENT_PROJECTS]
            self._write(records)
            return records

    def clear(self) -> None:
        with self._lock:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                raise

    def _write(self, records: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": PREFERENCES_SCHEMA_VERSION,
            "recent_projects": records,
        }
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(encoded) > MAX_PREFERENCES_BYTES:
            raise OSError("Inspector preferences exceeded the bounded size.")
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary.write_bytes(encoded)
            os.replace(temporary, self.path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
