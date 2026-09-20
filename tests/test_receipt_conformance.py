"""The offline reader gate uses Protocol's identical pinned synthetic cases."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_receipt_compatibility.py"
spec = importlib.util.spec_from_file_location("receipt_compatibility_checker", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class SharedReceiptConformanceTests(unittest.TestCase):
    def test_pinned_reader_cases_without_runtime_protocol_or_command_execution(self):
        with patch("subprocess.Popen", side_effect=AssertionError("Local reader conformance must not execute")):
            result = checker.run_checks()
        self.assertGreaterEqual(len(result["cases"]), 40)
        self.assertFalse(result["protocol_preview_executed"])
        self.assertEqual(result["failed"], 0, result)

    def test_manifest_or_fixture_tampering_is_detected(self):
        fixture, _ = checker.load_fixture()
        with self.assertRaises(AssertionError):
            fixture.load_corpus(checker.CORPUS, "0" * 64)
        for name in ("manifest.json", "cases.json", "fixture_helper.py"):
            with self.subTest(file=name), tempfile.TemporaryDirectory() as directory:
                copied = Path(directory) / "corpus"
                shutil.copytree(checker.CORPUS, copied)
                with (copied / name).open("ab") as stream:
                    stream.write(b"\n ")
                with self.assertRaises(AssertionError):
                    checker.verify_corpus(copied)


if __name__ == "__main__":
    unittest.main()
