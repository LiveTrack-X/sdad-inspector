from __future__ import annotations

from pathlib import Path
from contextlib import redirect_stderr
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import build_native
from sdad_inspector.engine import EngineInfo
from sdad_inspector.errors import EngineError, PackageError


class BuildVersionAlignmentTests(unittest.TestCase):
    def engine(self, version: str) -> EngineInfo:
        return EngineInfo("fixture", version, "v" + version, "a" * 40, None, "release", True)

    def test_matching_authenticated_engine_can_build(self) -> None:
        with patch.object(build_native, "probe_engine", return_value=self.engine(build_native.VERSION)), \
                patch.object(build_native, "_required_paths", return_value={"web_bundle": Path(__file__)}):
            result = build_native.check_prerequisites("fixture")
        self.assertTrue(result["ready"])
        self.assertEqual(result["product_version"], build_native.VERSION)
        self.assertEqual(result["release_tag"], "v" + build_native.VERSION)

    def test_older_supported_engine_cannot_be_bundled_under_new_product_version(self) -> None:
        with patch.object(build_native, "probe_engine", return_value=self.engine("3.2.3")), \
                patch.object(build_native, "_required_paths") as paths:
            with self.assertRaises(PackageError) as caught:
                build_native.check_prerequisites("fixture")
        self.assertEqual(caught.exception.details, {"product_version": build_native.VERSION, "engine_version": "3.2.3"})
        paths.assert_not_called()

    def test_matching_label_does_not_bypass_engine_authentication(self) -> None:
        with patch.object(build_native, "probe_engine", side_effect=EngineError("invalid release tree")):
            with self.assertRaises(EngineError):
                build_native.check_prerequisites("fixture")

    def test_checkout_changed_during_frontend_build_cannot_reach_packager(self) -> None:
        evidence = {"release_tag": "v" + build_native.VERSION, "revision": "a" * 40}
        stage = SimpleNamespace(engine=self.engine("3.2.3"), path=Path("fixture"))
        with patch.object(build_native.sys, "argv", ["build_native.py", "--sdad-checkout", "fixture", "--skip-frontend"]), \
                patch.object(build_native, "check_prerequisites", return_value=evidence), \
                patch.object(build_native, "require_release_python", return_value={}), \
                patch.object(build_native, "stage_release_engine", return_value=stage), \
                patch.object(build_native, "_run") as package, redirect_stderr(io.StringIO()) as error:
            self.assertEqual(build_native.main(), 2)
        package.assert_not_called()
        self.assertIn("changed after the native prerequisite check", error.getvalue())
