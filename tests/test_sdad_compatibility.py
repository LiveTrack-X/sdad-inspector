from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sdad_compatibility.py"
SPEC = importlib.util.spec_from_file_location("validate_sdad_compatibility", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SdadCompatibilityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MODULE.MANIFEST_PATH.read_text(encoding="utf-8"))

    def fixture_paths(self) -> list[Path]:
        return [
            ROOT / report["path"]
            for release in self.manifest["releases"].values()
            for report in release["reports"]
        ]

    def test_manifest_has_exact_release_and_scenario_sets(self) -> None:
        self.assertEqual(set(self.manifest["releases"]), set(MODULE.RELEASES))
        for release in self.manifest["releases"].values():
            self.assertEqual(
                {report["scenario"] for report in release["reports"]},
                set(MODULE.SCENARIOS),
            )

    def test_frozen_manifest_and_reports_validate(self) -> None:
        self.assertEqual(MODULE.validate_manifest(), 8)

    def test_validation_is_read_only_for_golden_files(self) -> None:
        paths = [MODULE.MANIFEST_PATH, *self.fixture_paths()]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(MODULE.validate_manifest(), 8)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(after, before)

    def test_cli_success_is_machine_readable_and_bounded(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = MODULE.main([])
        self.assertEqual(code, 0)
        self.assertEqual(
            output.getvalue(),
            "SDAD compatibility contract OK: 2 releases, 8 normalized reports.\n",
        )


if __name__ == "__main__":
    unittest.main()
