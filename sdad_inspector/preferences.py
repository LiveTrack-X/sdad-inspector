from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PREFERENCES_SCHEMA_VERSION = 1
MAX_RECENT_PROJECTS = 6
MAX_PREFERENCES_BYTES = 64 * 1024
MAX_PATH_CHARS = 4096
MAX_NAME_CHARS = 255
UI_THEMES = frozenset({"light", "dark"})
UI_LOCALES = frozenset({"en", "ko", "ja", "zh-CN"})
UI_SCALES = frozenset(range(90, 151, 10))


def default_preferences_path(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
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


def _validated_ui_preferences(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != PREFERENCES_SCHEMA_VERSION:
        return {}
    raw = payload.get("ui")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, Any] = {}
    theme = raw.get("theme")
    locale = raw.get("locale")
    scale = raw.get("scale")
    if isinstance(theme, str) and theme in UI_THEMES:
        result["theme"] = theme
    if isinstance(locale, str) and locale in UI_LOCALES:
        result["locale"] = locale
    if isinstance(scale, int) and not isinstance(scale, bool) and scale in UI_SCALES:
        result["scale"] = scale
    return result


class RecentProjectsStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_preferences_path()
        self._lock = threading.RLock()

    def load(self) -> list[dict[str, str]]:
        with self._lock:
            return _validated_records(self._read_payload())

    def load_ui_preferences(self) -> dict[str, Any]:
        with self._lock:
            return _validated_ui_preferences(self._read_payload())

    def latest_existing_project(self) -> Path | None:
        for record in self.load():
            candidate = Path(record["path"]).expanduser()
            try:
                if candidate.is_dir():
                    return candidate
            except OSError:
                continue
        return None

    def update_ui_preferences(
        self,
        *,
        theme: str | None = None,
        locale: str | None = None,
        scale: int | None = None,
    ) -> dict[str, Any]:
        if theme is not None and theme not in UI_THEMES:
            raise ValueError("Unsupported UI theme.")
        if locale is not None and locale not in UI_LOCALES:
            raise ValueError("Unsupported UI locale.")
        if scale is not None and scale not in UI_SCALES:
            raise ValueError("Unsupported UI scale.")
        with self._lock:
            payload = self._read_payload()
            records = _validated_records(payload)
            preferences = _validated_ui_preferences(payload)
            if theme is not None:
                preferences["theme"] = theme
            if locale is not None:
                preferences["locale"] = locale
            if scale is not None:
                preferences["scale"] = scale
            self._write(records, preferences)
            return preferences

    def remember(self, projects: Iterable[tuple[str | Path, str]]) -> list[dict[str, str]]:
        with self._lock:
            payload = self._read_payload()
            records = _validated_records(payload)
            preferences = _validated_ui_preferences(payload)
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
            self._write(records, preferences)
            return records

    def clear(self) -> None:
        with self._lock:
            preferences = self.load_ui_preferences()
            if preferences:
                self._write([], preferences)
            else:
                self.path.unlink(missing_ok=True)

    def _read_payload(self) -> object:
        try:
            if not self.path.is_file() or self.path.stat().st_size > MAX_PREFERENCES_BYTES:
                return {}
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}

    def _write(
        self,
        records: list[dict[str, str]],
        ui_preferences: Mapping[str, Any] | None = None,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": PREFERENCES_SCHEMA_VERSION,
            "recent_projects": records,
        }
        validated_ui = _validated_ui_preferences(
            {
                "schema_version": PREFERENCES_SCHEMA_VERSION,
                "ui": dict(ui_preferences or {}),
            }
        )
        if validated_ui:
            payload["ui"] = validated_ui
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
