from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from sdad_inspector.errors import ReportError
from sdad_inspector.report import render_static_report, write_static_report
from sdad_inspector.snapshot import inspect_project

from test_core import WorkspaceCase, tree_fingerprint


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.attributes: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag.casefold())
        self.attributes.extend(name.casefold() for name, _ in attrs)


class StaticReportTests(WorkspaceCase):
    def snapshot(self):
        return inspect_project(
            self.project,
            self.engine,
            _engine_info=self.engine_info,
        )

    def test_untrusted_repository_text_is_escaped_and_no_active_surface_exists(self) -> None:
        snapshot = self.snapshot()
        snapshot["state"]["active_packet"]["objective"] = (
            '<script>alert("owned")</script><img src="https://evil.invalid/x">'
        )
        document = render_static_report(snapshot)
        self.assertIn("&lt;script&gt;alert", document)
        self.assertIn("&lt;img src=&quot;https://evil.invalid/x&quot;&gt;", document)
        parser = SurfaceParser()
        parser.feed(document)
        for forbidden in ("script", "link", "iframe", "object", "embed"):
            self.assertNotIn(forbidden, parser.tags)
        self.assertNotIn("href", parser.attributes)
        self.assertNotIn("src", parser.attributes)
        self.assertIn("Content-Security-Policy", document)
        self.assertIn('data-read-only="true"', document)

    def test_path_and_evidence_redaction_remove_machine_values_and_hashes(self) -> None:
        snapshot = self.snapshot()
        known_hash = snapshot["evidence"]["files"]["sdad-state.yaml"]["sha256"]
        document = render_static_report(
            snapshot,
            redact_paths=True,
            redact_evidence=True,
        )
        self.assertNotIn(snapshot["project"]["root"], document)
        self.assertNotIn(snapshot["engine"]["checkout"], document)
        self.assertNotIn(known_hash, document)
        self.assertIn("&lt;PROJECT_ROOT&gt;", document)
        self.assertIn("evidence_redacted", document)

    def test_output_is_outside_project_atomic_and_does_not_modify_project(self) -> None:
        snapshot = self.snapshot()
        output = self.root / "reports" / "inspection.html"
        output.parent.mkdir()
        before = tree_fingerprint(self.project)
        result = write_static_report(snapshot, output)
        after = tree_fingerprint(self.project)
        self.assertEqual(before, after)
        self.assertEqual(Path(result["output"]), output)
        self.assertTrue(output.is_file())
        self.assertGreater(result["bytes"], 1000)
        self.assertFalse(any(output.parent.glob(f".{output.name}.*.tmp")))

    def test_existing_output_is_protected_without_explicit_overwrite(self) -> None:
        snapshot = self.snapshot()
        output = self.root / "report.html"
        output.write_text("owner content", encoding="utf-8")
        with self.assertRaises(ReportError):
            write_static_report(snapshot, output)
        self.assertEqual(output.read_text(encoding="utf-8"), "owner content")
        result = write_static_report(snapshot, output, overwrite=True)
        self.assertTrue(result["overwritten"])
        self.assertIn("<!doctype html>", output.read_text(encoding="utf-8"))

    def test_output_inside_inspected_project_is_rejected(self) -> None:
        snapshot = self.snapshot()
        with self.assertRaises(ReportError):
            write_static_report(snapshot, self.project / "inspection.html")
        self.assertFalse((self.project / "inspection.html").exists())

    def test_rendering_uses_the_snapshot_without_rereading_current_state(self) -> None:
        snapshot = self.snapshot()
        original_objective = snapshot["state"]["active_packet"]["objective"]
        self.write_state()
        state_path = self.project / "sdad-state.yaml"
        state_path.write_text(
            state_path.read_text(encoding="utf-8").replace(
                "Prove the read-only core.", "CHANGED AFTER SNAPSHOT"
            ),
            encoding="utf-8",
        )
        before = tree_fingerprint(self.project)
        document = render_static_report(snapshot)
        after = tree_fingerprint(self.project)
        self.assertEqual(before, after)
        self.assertIn(original_objective, document)
        self.assertNotIn("CHANGED AFTER SNAPSHOT", document)


if __name__ == "__main__":
    import unittest

    unittest.main()
