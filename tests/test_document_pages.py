from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from sdad_inspector.document_pages import DocumentPageError, _context_argv, read_document_page
from sdad_inspector.engine import authenticate_release_archive
from sdad_inspector.errors import EngineError, InspectorError
from sdad_inspector.native_entry import run_bundled_engine
from sdad_inspector.packaging import stage_release_engine
from sdad_inspector.preferences import RecentProjectsStore
from sdad_inspector.protocols import OfficialSdad3Adapter
from sdad_inspector.server import InspectorService, create_server
from sdad_inspector.state import load_control_state, load_live_documents
from test_core import WorkspaceCase, tree_fingerprint


def _document_runtime(root, add_cleanup):
    runtime = root / ".runtime" / "sdad-v3.2.4"
    if runtime.exists():
        return runtime
    checkout = root / ".ci" / "sdad-v3.2.4"
    if checkout.exists():
        temporary = tempfile.TemporaryDirectory(prefix="sdad-document-runtime-")
        add_cleanup(temporary.cleanup)
        runtime = Path(temporary.name).resolve() / "sdad-engine"
        stage_release_engine(checkout, runtime)
        return runtime
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        raise RuntimeError("CI requires the authenticated SDAD 3.2.4 checkout at .ci/sdad-v3.2.4 or a staged .runtime/sdad-v3.2.4.")
    raise unittest.SkipTest("Authenticated SDAD 3.2.4 runtime or CI checkout is not present in this local checkout.")


class DocumentRuntimePreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_existing_local_runtime_is_used_without_staging(self):
        runtime = self.root / ".runtime" / "sdad-v3.2.4"
        runtime.mkdir(parents=True)
        with patch(__name__ + ".stage_release_engine") as stage:
            self.assertEqual(_document_runtime(self.root, self.addCleanup), runtime)
        stage.assert_not_called()

    def test_ci_checkout_stages_into_temporary_directory_and_registers_cleanup(self):
        checkout = self.root / ".ci" / "sdad-v3.2.4"
        checkout.mkdir(parents=True)
        cleanups = []
        def stage(source, destination):
            self.assertEqual(source, checkout)
            self.assertFalse(destination.is_relative_to(self.root))
            destination.mkdir()
        try:
            with patch(__name__ + ".stage_release_engine", side_effect=stage) as staged:
                runtime = _document_runtime(self.root, cleanups.append)
            staged.assert_called_once_with(checkout, runtime)
            self.assertTrue(runtime.is_dir())
            self.assertEqual(len(cleanups), 1)
        finally:
            for cleanup in cleanups:
                cleanup()
        self.assertFalse(runtime.parent.exists())
        self.assertTrue(checkout.is_dir())

    def test_missing_ci_runtime_is_an_error_not_a_skip(self):
        for variable in ("CI", "GITHUB_ACTIONS"):
            with self.subTest(variable=variable), patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": "", variable: "true"}):
                with self.assertRaisesRegex(RuntimeError, "CI requires"):
                    _document_runtime(self.root, self.addCleanup)

    def test_thin_local_checkout_has_an_explicit_skip(self):
        with patch.dict(os.environ, {"CI": "", "GITHUB_ACTIONS": ""}):
            with self.assertRaisesRegex(unittest.SkipTest, "local checkout"):
                _document_runtime(self.root, self.addCleanup)


class DocumentPageTests(WorkspaceCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = _document_runtime(Path(__file__).resolve().parents[1], cls.addClassCleanup)
        cls.authenticated = authenticate_release_archive(cls.runtime)

    def page(self, path="SPEC/SPEC-COMPLETE.md", **options):
        return read_document_page(self.project, self.authenticated, OfficialSdad3Adapter(), {"path": path, **options})

    def test_large_ledgers_remain_discoverable_and_pages_are_pinned_without_project_execution(self):
        todo = self.project / "docs/TODO-Open-Items.md"
        todo.write_text("# TODO\n\n## Active Work\n" + "\n".join(f"- [ ] [packet:CORE-1] Work {index}" for index in range(720)) + "\n", encoding="utf-8")
        findings = self.project / "review-findings.md"
        findings.write_text("# Findings\n\n## Active Findings\n" + "\n".join(f"- [High] [packet:CORE-1] Finding {index}" for index in range(720)) + "\n", encoding="utf-8")
        shadow = self.project / "sdad_validator"
        shadow.mkdir()
        (shadow / "__init__.py").write_text("raise RuntimeError('project Python must never execute')", encoding="utf-8")
        before = tree_fingerprint(self.project)
        state, _ = load_control_state(self.project)
        self.assertFalse(state["ledger"]["todo_complete"])
        self.assertFalse(state["ledger"]["review_findings_complete"])
        self.assertGreater(state["ledger"]["todo_open"], 0)
        self.assertLess(state["ledger"]["todo_open"], 720)
        documents = load_live_documents(self.project)
        preview = next(item for item in documents["documents"] if item["path"] == "docs/TODO-Open-Items.md")
        self.assertEqual(preview["project_root"], str(self.project))
        self.assertTrue(preview["truncated"])
        self.assertEqual(len(preview["content"].splitlines()), 500)
        first = self.page(preview["path"], lines=500, expected_sha256=preview["sha256"])
        following = self.page(preview["path"], start=first["next_start"], lines=500, expected_sha256=first["sha256"])
        self.assertEqual(first["lines"] + following["lines"], todo.read_text(encoding="utf-8").splitlines())
        self.assertFalse(following["truncated"])
        self.assertEqual(following["file_lines"], 723)
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_missing_or_unreadable_ledger_is_not_a_complete_zero(self):
        (self.project / "docs/TODO-Open-Items.md").unlink()
        (self.project / "review-findings.md").write_bytes(b"\xff")
        state, _ = load_control_state(self.project)
        self.assertFalse(state["ledger"]["todo_complete"])
        self.assertFalse(state["ledger"]["review_findings_complete"])

    def test_source_changed_continuation_is_rejected_and_restart_observes_new_revision(self):
        path = self.project / "SPEC/SPEC-COMPLETE.md"
        path.write_text("\n".join(f"line {index}" for index in range(120)), encoding="utf-8")
        first = self.page()
        path.write_text("changed\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
        with self.assertRaises(DocumentPageError) as failure:
            self.page(start=first["next_start"], expected_sha256=first["sha256"])
        self.assertEqual(failure.exception.code, "document_changed")
        restarted = self.page()
        self.assertNotEqual(restarted["sha256"], first["sha256"])
        self.assertEqual(restarted["lines"][0], "changed")

    def test_unrouted_sensitive_traversal_and_hardlinks_are_rejected(self):
        (self.project / "unrouted.md").write_text("private", encoding="utf-8")
        (self.project / ".env").write_text("private", encoding="utf-8")
        for path in ("unrouted.md", ".env", "../outside.md", "docs/../unrouted.md", str(self.project / "unrouted.md")):
            with self.subTest(path=path), self.assertRaises(InspectorError):
                self.page(path)
        source = self.project / "SPEC/SPEC-COMPLETE.md"
        linked = self.root / "linked-spec"
        os.link(source, linked)
        with self.assertRaises(InspectorError):
            self.page()

    def test_invalid_ranges_and_unpinned_continuations_are_rejected(self):
        for options in ({"start": 0}, {"start": True}, {"lines": 501}, {"lines": False}, {"start": 2}, {"expected_sha256": "not-a-hash"}):
            with self.subTest(options=options), self.assertRaises(DocumentPageError):
                self.page(**options)

    def test_file_line_and_serialized_page_budgets_remain_bounded(self):
        path = self.project / "SPEC/SPEC-COMPLETE.md"
        for content in (b"x" * 1_000_001, b"x" * 50_001, b"\xff"):
            path.write_bytes(content)
            with self.subTest(bytes=len(content)), self.assertRaises(DocumentPageError):
                self.page()
        path.write_text(("\"\\" * 900 + "\n") * 200, encoding="utf-8")
        page = self.page(lines=500)
        self.assertLess(len(page["lines"]), 200)
        self.assertLessEqual(page["page_bytes"], 50_000)
        self.assertIsNotNone(page["next_start"])

    def test_untrusted_engine_is_rejected_before_reader_execution(self):
        with patch("sdad_inspector.document_pages._run") as run:
            with self.assertRaises(EngineError):
                read_document_page(self.project, self.engine_info, OfficialSdad3Adapter(), {"path": "SPEC/SPEC-COMPLETE.md"})
            run.assert_not_called()

    def test_endpoint_requires_token_origin_and_exact_selected_project(self):
        service = InspectorService(self.project, self.runtime, engine_info=self.authenticated,
                                   preferences_store=RecentProjectsStore(self.root / "app/preferences.json"))
        web = self.root / "web"
        web.mkdir()
        (web / "index.html").write_text("<!doctype html><title>Fixture</title>", encoding="utf-8")
        server = create_server(service, web, session_token="page-token")
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        def request(payload, *, token=True, origin=True):
            headers = {"Content-Type": "application/json"}
            if token: headers["X-SDAD-Session"] = "page-token"
            if origin: headers["Origin"] = server.origin
            request = urllib.request.Request(server.origin + "/api/documents/page", data=json.dumps(payload).encode(), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)
        payload = {"project_root": str(self.project), "path": "SPEC/SPEC-COMPLETE.md"}
        before = tree_fingerprint(self.project)
        try:
            self.assertEqual(request(payload, token=False)[0], 403)
            self.assertEqual(request(payload, origin=False)[0], 403)
            status, page = request(payload)
            self.assertEqual(status, 200)
            self.assertEqual(page["project_root"], str(self.project))
            other = self.root / "other-project"
            shutil.copytree(self.project, other)
            service.open_project(str(other))
            status, error = request(payload)
            self.assertEqual(status, 422)
            self.assertEqual(error["error"]["code"], "document_page_project")
            self.assertEqual(tree_fingerprint(self.project), before)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_frozen_context_runner_uses_only_authenticated_bundle_and_restores_globals(self):
        bundle = self.root / "bundle"
        shutil.copytree(self.runtime, bundle / "sdad-engine")
        original_path, original_argv = sys.path[:], sys.argv[:]
        output = io.StringIO()
        with patch("sdad_inspector.native_entry.resource_root", return_value=bundle), contextlib.redirect_stdout(output):
            result = run_bundled_engine(["--root", str(self.project), "read", "SPEC/SPEC-COMPLETE.md"], context=True)
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["lines"], ["# Fixture SPEC"])
        self.assertEqual(sys.path, original_path)
        self.assertEqual(sys.argv, original_argv)
        import sdad_inspector.document_pages as paging
        script = bundle / "sdad-engine/scripts/sdad_context.py"
        with patch.object(paging, "__file__", str(bundle / "sdad_inspector/document_pages.py")), patch.object(sys, "frozen", True, create=True):
            self.assertEqual(_context_argv(script, ["read"])[1:], ["--sdad-internal-context", "read"])
            with self.assertRaises(DocumentPageError):
                _context_argv(self.runtime / "scripts/sdad_context.py", ["read"])
