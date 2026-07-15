from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sdad_inspector.preferences import (
    MAX_PREFERENCES_BYTES,
    RecentProjectsStore,
    default_preferences_path,
)


class RecentProjectsStoreTests(unittest.TestCase):
    def test_platform_paths_are_stable_and_do_not_depend_on_loopback_origin(self) -> None:
        home = Path("/home/owner")
        self.assertEqual(
            default_preferences_path(
                platform="win32",
                environ={"LOCALAPPDATA": "C:/Users/owner/AppData/Local"},
                home=home,
            ).as_posix(),
            "C:/Users/owner/AppData/Local/SDAD Inspector/preferences.json",
        )
        self.assertEqual(
            default_preferences_path(platform="darwin", environ={}, home=home),
            home / "Library" / "Application Support" / "SDAD Inspector" / "preferences.json",
        )
        self.assertEqual(
            default_preferences_path(platform="linux", environ={}, home=home),
            home / ".config" / "sdad-inspector" / "preferences.json",
        )

    def test_successive_project_switches_persist_six_deduplicated_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "preferences.json"
            store = RecentProjectsStore(path)
            for index in range(8):
                store.remember(((f"C:/projects/{index}", f"project-{index}"),))
            records = store.load()
            self.assertEqual(len(records), 6)
            self.assertEqual(records[0]["path"], "C:/projects/7")
            store.remember((("C:/projects/4", "project-4"),))
            self.assertEqual(RecentProjectsStore(path).load()[0]["path"], "C:/projects/4")

    def test_malformed_or_oversized_preferences_are_ignored_and_clear_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "preferences.json"
            store = RecentProjectsStore(path)
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(store.load(), [])
            path.write_bytes(b"x" * (MAX_PREFERENCES_BYTES + 1))
            self.assertEqual(store.load(), [])
            path.write_text(
                json.dumps({"schema_version": 99, "recent_projects": []}),
                encoding="utf-8",
            )
            self.assertEqual(store.load(), [])
            store.clear()
            self.assertFalse(path.exists())
            store.clear()


if __name__ == "__main__":
    unittest.main()
