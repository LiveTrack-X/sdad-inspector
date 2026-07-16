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

    def test_ui_preferences_survive_project_history_changes_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "preferences.json"
            project = root / "project"
            project.mkdir()
            store = RecentProjectsStore(path)

            self.assertEqual(
                store.update_ui_preferences(theme="dark", locale="ja", scale=130),
                {"theme": "dark", "locale": "ja", "scale": 130},
            )
            store.remember(((project, "project"),))
            self.assertEqual(store.latest_existing_project(), project)
            store.clear()

            reopened = RecentProjectsStore(path)
            self.assertEqual(reopened.load(), [])
            self.assertEqual(
                reopened.load_ui_preferences(),
                {"theme": "dark", "locale": "ja", "scale": 130},
            )

    def test_invalid_ui_preferences_are_rejected_without_overwriting_valid_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = RecentProjectsStore(Path(temporary) / "preferences.json")
            store.update_ui_preferences(theme="dark", locale="zh-CN", scale=110)
            with self.assertRaises(ValueError):
                store.update_ui_preferences(theme="sepia")
            with self.assertRaises(ValueError):
                store.update_ui_preferences(locale="fr")
            with self.assertRaises(ValueError):
                store.update_ui_preferences(scale=115)
            self.assertEqual(
                store.load_ui_preferences(),
                {"theme": "dark", "locale": "zh-CN", "scale": 110},
            )


if __name__ == "__main__":
    unittest.main()
