from __future__ import annotations

import http.client
import json
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from sdad_inspector.preferences import RecentProjectsStore
from sdad_inspector.server import InspectorService, create_server

from test_core import WorkspaceCase, tree_fingerprint


class LoopbackServerTests(WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        self.web = self.root / "web-dist"
        self.web.mkdir()
        (self.web / "index.html").write_text(
            '<!doctype html><meta name="sdad-session" content="__SDAD_SESSION_TOKEN__"><div id="root"></div>',
            encoding="utf-8",
        )
        (self.web / "app.js").write_text("console.log('fixture')\n", encoding="utf-8")
        service = InspectorService(
            self.project,
            self.engine,
            engine_info=self.engine_info,
            project_picker=lambda _initial: str(self.project),
            clipboard_reader=lambda: f'"{self.project}"',
            preferences_store=RecentProjectsStore(self.root / "app-data" / "preferences.json"),
        )
        self.token = "fixed-test-session"
        self.server = create_server(service, self.web, session_token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        token: str | None = None,
        origin: bool = False,
        payload: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        headers: dict[str, str] = {}
        if token is not None:
            headers["X-SDAD-Session"] = token
        if origin:
            headers["Origin"] = self.server.origin
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.server.origin + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, dict(response.headers.items()), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()

    def test_index_injects_session_and_sets_browser_security_headers(self) -> None:
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(self.token.encode("ascii"), body)
        self.assertNotIn(b"__SDAD_SESSION_TOKEN__", body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_snapshot_requires_the_per_launch_session_token(self) -> None:
        denied, _, _ = self.request("/api/snapshot")
        self.assertEqual(denied, 403)
        status, headers, body = self.request("/api/snapshot", token=self.token)
        self.assertEqual(status, 200)
        snapshot = json.loads(body)
        self.assertTrue(snapshot["read_only"])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_live_documents_and_activity_are_authenticated_no_store_routes(self) -> None:
        denied, _, _ = self.request("/api/documents")
        self.assertEqual(denied, 403)
        status, headers, body = self.request("/api/documents", token=self.token)
        self.assertEqual(status, 200)
        documents = json.loads(body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("SPEC/SPEC-COMPLETE.md", {item["path"] for item in documents["documents"]})
        activity_status, activity_headers, activity_body = self.request(
            "/api/activity", token=self.token
        )
        self.assertEqual(activity_status, 200)
        self.assertEqual(activity_headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(activity_body)["worktree_status"], "unavailable")

    def test_product_update_routes_are_authenticated_and_source_mode_is_inert(self) -> None:
        denied, _, _ = self.request("/api/update")
        self.assertEqual(denied, 403)
        status, headers, body = self.request("/api/update", token=self.token)
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertFalse(payload["supported"])
        self.assertEqual(payload["state"], "unsupported")
        self.assertTrue(payload["automatic"])
        self.assertEqual(headers["Cache-Control"], "no-store")

        missing_origin, _, _ = self.request(
            "/api/update/check",
            method="POST",
            token=self.token,
            payload={},
        )
        self.assertEqual(missing_origin, 403)
        check_status, _, check_body = self.request(
            "/api/update/check",
            method="POST",
            token=self.token,
            origin=True,
            payload={},
        )
        self.assertEqual(check_status, 200)
        self.assertEqual(json.loads(check_body)["state"], "unsupported")

    def test_picker_and_explicit_paste_do_not_switch_projects(self) -> None:
        before = self.server.service.snapshot()["project"]["root"]
        picker_status, _, picker_body = self.request(
            "/api/project-picker",
            method="POST",
            token=self.token,
            origin=True,
            payload={"initial_path": str(self.project)},
        )
        self.assertEqual(picker_status, 200)
        self.assertTrue(json.loads(picker_body)["selected"])
        paste_status, _, paste_body = self.request(
            "/api/clipboard/project-path",
            method="POST",
            token=self.token,
            origin=True,
            payload={},
        )
        self.assertEqual(paste_status, 200)
        self.assertEqual(Path(json.loads(paste_body)["project_root"]), self.project)
        self.assertEqual(self.server.service.snapshot()["project"]["root"], before)

    def test_progress_requires_session_and_reports_a_bounded_observed_lifecycle(self) -> None:
        denied, _, _ = self.request("/api/progress")
        self.assertEqual(denied, 403)
        status, headers, body = self.request("/api/progress", token=self.token)
        self.assertEqual(status, 200)
        progress = json.loads(body)
        self.assertEqual(progress["status"], "completed")
        self.assertEqual(progress["kind"], "initial")
        self.assertEqual(progress["stage"], "report")
        self.assertEqual(progress["stage_count"], 5)
        self.assertLessEqual(len(progress["recent"]), 8)
        self.assertNotIn("percent", progress)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_progress_remains_visible_while_a_rescan_request_is_running(self) -> None:
        started = threading.Event()
        release = threading.Event()
        previous = self.server.service.snapshot()

        def slow_inspection(*args, progress_callback=None, **kwargs):
            assert progress_callback is not None
            progress_callback("doctor", "scripts/sdad.py", "doctor_started")
            started.set()
            self.assertTrue(release.wait(timeout=5))
            return {**previous, "inspection_id": "concurrent-progress"}

        errors: list[BaseException] = []

        def run_rescan() -> None:
            try:
                self.server.service.rescan()
            except BaseException as exc:  # pragma: no cover - reported below
                errors.append(exc)

        with patch("sdad_inspector.server.inspect_project", side_effect=slow_inspection):
            worker = threading.Thread(target=run_rescan, daemon=True)
            worker.start()
            self.assertTrue(started.wait(timeout=5))
            live = self.server.service.progress()
            self.assertEqual(live["status"], "running")
            self.assertEqual(live["stage"], "doctor")
            self.assertEqual(live["current_source"], "scripts/sdad.py")
            release.set()
            worker.join(timeout=5)

        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.server.service.progress()["status"], "completed")

    def test_host_and_origin_are_enforced_without_cors(self) -> None:
        host, port = self.server.server_address[:2]
        connection = http.client.HTTPConnection(host, port, timeout=5)
        connection.request(
            "GET",
            "/api/snapshot",
            headers={"Host": "evil.invalid", "X-SDAD-Session": self.token},
        )
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        response.read()
        connection.close()

        missing_origin, _, _ = self.request(
            "/api/rescan", method="POST", token=self.token, payload={}
        )
        self.assertEqual(missing_origin, 403)

    def test_rescan_uses_the_fixed_route_and_does_not_write_the_project(self) -> None:
        before = tree_fingerprint(self.project)
        status, _, body = self.request(
            "/api/rescan",
            method="POST",
            token=self.token,
            origin=True,
            payload={},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["doctor"]["exit_code"], 0)
        self.assertEqual(before, tree_fingerprint(self.project))

    def test_project_switch_replaces_the_snapshot_only_after_success(self) -> None:
        other = self.root / "another project"
        shutil.copytree(self.project, other)
        status, _, body = self.request(
            "/api/project",
            method="POST",
            token=self.token,
            origin=True,
            payload={"project_root": str(other)},
        )
        self.assertEqual(status, 200)
        self.assertEqual(Path(json.loads(body)["project"]["root"]), other.resolve())
        _, _, snapshot_body = self.request("/api/snapshot", token=self.token)
        self.assertEqual(Path(json.loads(snapshot_body)["project"]["root"]), other.resolve())

        recent_status, recent_headers, recent_body = self.request(
            "/api/recent-projects", token=self.token
        )
        self.assertEqual(recent_status, 200)
        self.assertEqual(recent_headers["Cache-Control"], "no-store")
        records = json.loads(recent_body)["recent_projects"]
        self.assertEqual(Path(records[0]["path"]), other.resolve())
        self.assertEqual(Path(records[1]["path"]), self.project.resolve())
        self.assertFalse((other / "preferences.json").exists())

        clear_status, _, clear_body = self.request(
            "/api/recent-projects/clear",
            method="POST",
            token=self.token,
            origin=True,
            payload={},
        )
        self.assertEqual(clear_status, 200)
        self.assertEqual(json.loads(clear_body)["recent_projects"], [])
        after_clear, _, after_clear_body = self.request(
            "/api/recent-projects", token=self.token
        )
        self.assertEqual(after_clear, 200)
        self.assertEqual(json.loads(after_clear_body)["recent_projects"], [])

    def test_rule5_preview_and_explicit_save_as_export_leave_project_unchanged(self) -> None:
        (self.project / "review-findings.md").write_text(
            "# Review Findings\n\n## Active Findings\n\n"
            "- [Medium] [packet:CORE-1] [FIND-R5-HTTP] A missing control recurred.\n"
            "  Root cause: The flow omitted a durable check.\n"
            "  Operational rule: Require the check before the protected action.\n"
            "  Enforcement: A deterministic validator blocks missing checks.\n"
            "  Regression evidence: tests/test_rule.py covers both outcomes.\n"
            "  Review condition: Keep, Refine, Merge, or Retire after field use.\n\n"
            "## Recently Closed\n",
            encoding="utf-8",
        )
        before = tree_fingerprint(self.project)
        status, headers, body = self.request(
            "/api/rule5-candidates", token=self.token
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        candidate = json.loads(body)["candidates"][0]

        preview_status, _, preview_body = self.request(
            "/api/rule5/preview",
            method="POST",
            token=self.token,
            origin=True,
            payload=candidate,
        )
        self.assertEqual(preview_status, 200)
        preview = json.loads(preview_body)
        self.assertIn("Rule 5 Proposal", preview["markdown"])
        self.assertEqual(before, tree_fingerprint(self.project))

        unconfirmed_status, _, _ = self.request(
            "/api/rule5/export",
            method="POST",
            token=self.token,
            origin=True,
            payload={**candidate, "confirmed": False, "preview_sha256": preview["sha256"]},
        )
        self.assertEqual(unconfirmed_status, 422)
        mismatched_status, _, _ = self.request(
            "/api/rule5/export",
            method="POST",
            token=self.token,
            origin=True,
            payload={**candidate, "confirmed": True, "preview_sha256": "0" * 64},
        )
        self.assertEqual(mismatched_status, 422)
        self.assertEqual(before, tree_fingerprint(self.project))

        self.server.service.set_rule_export_picker(
            lambda _suggested: str(self.project / "proposal.md")
        )
        inside_project_status, _, _ = self.request(
            "/api/rule5/export",
            method="POST",
            token=self.token,
            origin=True,
            payload={**candidate, "confirmed": True, "preview_sha256": preview["sha256"]},
        )
        self.assertEqual(inside_project_status, 422)
        self.assertFalse((self.project / "proposal.md").exists())
        self.assertEqual(before, tree_fingerprint(self.project))

        self.server.service.set_rule_export_picker(lambda _suggested: None)
        cancelled_status, _, cancelled_body = self.request(
            "/api/rule5/export",
            method="POST",
            token=self.token,
            origin=True,
            payload={**candidate, "confirmed": True, "preview_sha256": preview["sha256"]},
        )
        self.assertEqual(cancelled_status, 200)
        self.assertTrue(json.loads(cancelled_body)["cancelled"])
        self.assertEqual(before, tree_fingerprint(self.project))

        destination = self.root / "exports" / "rule-proposal"
        destination.parent.mkdir()
        self.server.service.set_rule_export_picker(lambda _suggested: str(destination))
        saved_status, _, saved_body = self.request(
            "/api/rule5/export",
            method="POST",
            token=self.token,
            origin=True,
            payload={**candidate, "confirmed": True, "preview_sha256": preview["sha256"]},
        )
        self.assertEqual(saved_status, 200)
        saved = json.loads(saved_body)
        self.assertTrue(saved["saved"])
        exported = destination.with_suffix(".md")
        self.assertEqual(exported.read_text(encoding="utf-8"), preview["markdown"])
        self.assertEqual(before, tree_fingerprint(self.project))

        (self.project / "review-findings.md").write_text(
            (self.project / "review-findings.md").read_text(encoding="utf-8") + "\nchanged\n",
            encoding="utf-8",
        )
        stale_status, _, _ = self.request(
            "/api/rule5/export",
            method="POST",
            token=self.token,
            origin=True,
            payload={**candidate, "confirmed": True, "preview_sha256": preview["sha256"]},
        )
        self.assertEqual(stale_status, 422)

    def test_undeclared_routes_and_preflight_are_closed(self) -> None:
        unknown, _, _ = self.request("/api/run", token=self.token)
        self.assertEqual(unknown, 404)
        options, headers, _ = self.request("/api/snapshot", method="OPTIONS")
        self.assertEqual(options, 405)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        traversal, _, _ = self.request("/%2e%2e/pyproject.toml")
        self.assertEqual(traversal, 404)


if __name__ == "__main__":
    import unittest

    unittest.main()
