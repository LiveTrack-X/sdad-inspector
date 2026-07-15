from __future__ import annotations

import unittest
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
