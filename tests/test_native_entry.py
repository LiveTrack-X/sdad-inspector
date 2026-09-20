from __future__ import annotations

import unittest
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

from sdad_inspector import native_entry


class FrozenWindowsIconTests(unittest.TestCase):
    def test_frozen_windows_refreshes_running_executable(self) -> None:
        with (
            patch.object(native_entry.sys, "platform", "win32"),
            patch.object(native_entry.sys, "frozen", True, create=True),
            patch.object(native_entry.sys, "executable", "C:/portable/SDAD-Inspector.exe"),
            patch.object(native_entry, "refresh_windows_icon_cache", return_value=True) as refresh,
        ):
            self.assertTrue(native_entry.refresh_frozen_windows_icon())

        refresh.assert_called_once_with(Path("C:/portable/SDAD-Inspector.exe"))

    def test_source_mode_and_non_windows_are_noops(self) -> None:
        for platform_name, frozen in (("win32", False), ("linux", True)):
            with self.subTest(platform_name=platform_name, frozen=frozen):
                with (
                    patch.object(native_entry.sys, "platform", platform_name),
                    patch.object(native_entry.sys, "frozen", frozen, create=True),
                    patch.object(native_entry, "refresh_windows_icon_cache") as refresh,
                ):
                    self.assertFalse(native_entry.refresh_frozen_windows_icon())
                refresh.assert_not_called()

    def test_refresh_failure_never_blocks_startup(self) -> None:
        with (
            patch.object(native_entry.sys, "platform", "win32"),
            patch.object(native_entry.sys, "frozen", True, create=True),
            patch.object(native_entry, "refresh_windows_icon_cache", side_effect=OSError("shell")),
        ):
            self.assertFalse(native_entry.refresh_frozen_windows_icon())


class StartupProjectTests(unittest.TestCase):
    def test_no_argument_reopens_the_latest_existing_project(self) -> None:
        project = Path("C:/projects/latest")
        with (
            patch.object(native_entry, "refresh_frozen_windows_icon", return_value=False),
            patch.object(
                native_entry.RecentProjectsStore,
                "latest_existing_project",
                return_value=project,
            ),
            patch.object(native_entry, "run_desktop", return_value=0) as run_desktop,
        ):
            self.assertEqual(native_entry.main([]), 0)
        self.assertEqual(run_desktop.call_args.args[0], project)

    def test_first_launch_opens_desktop_without_invoking_a_native_folder_picker(self) -> None:
        with (
            patch.object(native_entry, "refresh_frozen_windows_icon", return_value=False),
            patch.object(
                native_entry.RecentProjectsStore,
                "latest_existing_project",
                return_value=None,
            ),
            patch.object(native_entry, "run_desktop", return_value=0) as run_desktop,
        ):
            self.assertEqual(native_entry.main([]), 0)
        self.assertIsNone(run_desktop.call_args.args[0])


class SmokePreferencesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "keep.txt").write_bytes(b"keep project unchanged")
        self.preferences = self.root / "isolated-app" / "preferences.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_explicit_hidden_smoke_uses_only_the_isolated_preferences_store(self) -> None:
        def desktop(project, _engine, _web, **options):
            self.assertEqual(project, self.project)
            self.assertTrue(options["hidden"])
            self.assertEqual(options["smoke_seconds"], 2)
            self.assertEqual(options["port"], 4242)
            store = options["preferences_store"]
            self.assertEqual(store.path, self.preferences)
            store.remember([(project, project.name)])
            return 0
        with (
            patch.object(native_entry, "refresh_frozen_windows_icon", return_value=False),
            patch("sdad_inspector.preferences.default_preferences_path", side_effect=AssertionError("Default user store accessed")),
            patch.object(native_entry.RecentProjectsStore, "latest_existing_project", side_effect=AssertionError("Explicit project ignored")),
            patch.object(native_entry, "run_desktop", side_effect=desktop),
        ):
            self.assertEqual(native_entry.main([str(self.project), "--hidden", "--smoke-seconds", "2", "--port", "4242", "--smoke-preferences", str(self.preferences)]), 0)
        self.assertTrue(self.preferences.is_file())
        self.assertEqual({p.name for p in self.project.iterdir()}, {"keep.txt"})
        self.assertEqual((self.project / "keep.txt").read_bytes(), b"keep project unchanged")

    def test_invalid_smoke_preferences_guards_reject_before_store_or_desktop_creation(self) -> None:
        valid = [str(self.project), "--hidden", "--smoke-seconds=2"]
        cases = [[str(self.project), "--smoke-seconds=2"],
                 [str(self.project), "--hidden"],
                 ["--hidden", "--smoke-seconds=2"],
                 *[[str(self.project), "--hidden", "--smoke-seconds=" + value] for value in ("nan", "inf", "-inf", "0", "-1")]]
        cases = [(args, self.preferences) for args in cases]
        cases.extend([(valid, self.project / "preferences.json"), (valid, self.project / "nested" / "preferences.json"), (valid, self.project)])
        for args, path in cases:
            with (
                self.subTest(args=args, path=path),
                patch.object(native_entry, "refresh_frozen_windows_icon", return_value=False),
                patch.object(native_entry, "RecentProjectsStore") as store,
                patch.object(native_entry, "run_desktop") as desktop,
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                native_entry.main([*args, "--smoke-preferences", str(path)])
            self.assertEqual(caught.exception.code, 2)
            store.assert_not_called()
            desktop.assert_not_called()
        self.assertFalse(self.preferences.parent.exists())
        self.assertEqual({p.name for p in self.project.iterdir()}, {"keep.txt"})

    def test_normal_explicit_startup_keeps_default_preferences_and_smoke_options_unset(self) -> None:
        with (
            patch.object(native_entry, "refresh_frozen_windows_icon", return_value=False),
            patch.object(native_entry, "RecentProjectsStore") as store,
            patch.object(native_entry, "run_desktop", return_value=0) as desktop,
        ):
            self.assertEqual(native_entry.main([str(self.project)]), 0)
        store.assert_called_once_with()
        store.return_value.latest_existing_project.assert_not_called()
        self.assertFalse(desktop.call_args.kwargs["hidden"])
        self.assertIsNone(desktop.call_args.kwargs["smoke_seconds"])
        self.assertIs(desktop.call_args.kwargs["preferences_store"], store.return_value)


if __name__ == "__main__":
    unittest.main()
