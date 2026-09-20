from __future__ import annotations

import http.client
import json
import shutil
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from sdad_inspector.preferences import RecentProjectsStore
from sdad_inspector.report import render_static_report
from sdad_inspector.server import InspectorService, create_server

from test_core import WorkspaceCase, tree_fingerprint


class LoopbackServerTests(WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        self.web = self.root / "web-dist"
        self.web.mkdir()
        (self.web / "index.html").write_text(
            '<!doctype html><meta name="sdad-session" content="__SDAD_SESSION_TOKEN__">'
            '<meta name="sdad-theme" content="__SDAD_THEME__">'
            '<meta name="sdad-locale" content="__SDAD_LOCALE__">'
            '<meta name="sdad-ui-scale" content="__SDAD_UI_SCALE__"><div id="root"></div>',
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

    def test_correction_api_requires_origin_and_exact_project_without_project_writes(self) -> None:
        draft = {"id": "C1", "request_id": "R1", "packet": "P1", "base_revision": "r1",
                 "project_root": str(self.server.service.project_root), "before": "browser", "correction": "account",
                 "supersedes": "", "copy_state": "draft"}
        before = tree_fingerprint(self.project)
        status, _, _ = self.request("/api/corrections", method="POST", token=self.token, payload=draft)
        self.assertEqual(status, 403)
        status, _, _ = self.request("/api/corrections", method="POST", token=self.token, origin=True, payload={**draft, "project_root": "other"})
        self.assertEqual(status, 422)
        status, _, body = self.request("/api/corrections", method="POST", token=self.token, origin=True, payload=draft)
        self.assertEqual(status, 200, body)
        status, _, body = self.request("/api/corrections", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["drafts"], [{**draft, "revision": 1}])
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_correction_store_inside_inspected_root_is_rejected(self) -> None:
        self.server.service._corrections.path = self.project / "corrections.json"
        before = tree_fingerprint(self.project)
        status, _, _ = self.request("/api/corrections", method="POST", token=self.token, origin=True,
                                   payload={"project_root": str(self.project)})
        self.assertEqual(status, 422)
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_history_reads_reject_storage_inside_project_before_creating_lock(self) -> None:
        self.server.service._corrections.path = self.project / "new-app-data" / "corrections.json"
        before = tree_fingerprint(self.project)
        status, _, body = self.request("/api/corrections", token=self.token)
        self.assertEqual(status, 422, body)
        status, _, body = self.request("/api/corrections/history", method="POST", token=self.token, origin=True, payload={"project_root": str(self.server.service.project_root)})
        self.assertEqual(status, 422, body)
        self.assertEqual(tree_fingerprint(self.project), before)
        self.assertFalse(self.server.service._corrections.path.parent.exists())

    def test_history_routes_confirm_actions_preserve_project_and_roundtrip_export(self) -> None:
        root = str(self.server.service.project_root)
        draft = {"id":"C-history", "request_id":"R1", "packet":"P1", "base_revision":"r1", "project_root":root, "before":"before", "correction":"full recovery text", "supersedes":"older", "copy_state":"copied"}
        before = tree_fingerprint(self.project)
        status, _, body = self.request("/api/corrections", method="POST", token=self.token, origin=True, payload=draft)
        self.assertEqual(status, 200, body)
        saved = json.loads(body)
        payload = {"project_root":root, "draft":saved}
        status, _, _ = self.request("/api/corrections/archive", method="POST", token=self.token, origin=True, payload=payload)
        self.assertEqual(status, 422)
        status, _, _ = self.request("/api/corrections/archive", method="POST", token=self.token, payload={**payload, "confirmed":True})
        self.assertEqual(status, 403)
        status, _, body = self.request("/api/corrections/archive", method="POST", token=self.token, origin=True, payload={**payload, "confirmed":True})
        self.assertEqual(status, 200, body)
        status, _, body = self.request("/api/corrections/history", method="POST", token=self.token, origin=True, payload={"project_root":root, "archived":True})
        self.assertEqual(json.loads(body)["drafts"], [saved])
        self.assertEqual(json.loads(body)["usage"]["active_count"], 0)
        bundle = {"schema_version":1,"kind":"sdad-correction-export","draft":saved}
        status, _, body = self.request("/api/corrections/import", method="POST", token=self.token, origin=True, payload={"project_root":root,"bundle":bundle})
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body), saved)
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_large_recovery_json_roundtrips_without_expanding_other_request_limits(self) -> None:
        root = str(self.server.service.project_root)
        draft = {"id":"C-large", "request_id":"R1", "packet":"P1", "base_revision":"r1", "project_root":root, "before":"한" * 4000, "correction":"글" * 4000, "supersedes":"x" * 4000, "copy_state":"copied", "revision":2}
        bundle = {"schema_version":1,"kind":"sdad-correction-export","draft":draft}
        # Escaped JSON transport is larger than ordinary 64 KiB requests.
        payload = {"project_root":root,"bundle":bundle,"padding":" " * 16000}
        self.assertGreater(len(json.dumps(payload).encode()), 65536)
        status, _, body = self.request("/api/corrections/import", method="POST", token=self.token, origin=True, payload=payload)
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body), draft)
        status, _, _ = self.request("/api/corrections", method="POST", token=self.token, origin=True, payload=payload)
        self.assertEqual(status, 413)
        status, _, _ = self.request("/api/corrections/import", method="POST", token=self.token, origin=True, payload={"project_root":root,"bundle":bundle,"padding":" " * (513 * 1024)})
        self.assertEqual(status, 413)

    def test_rejected_delayed_body_returns_denial_without_parsing_or_action(self) -> None:
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        before = tree_fingerprint(self.project)
        with patch.object(self.server.service, "rule5_preview") as action, patch("sdad_inspector.server.InspectorRequestHandler._read_json", side_effect=AssertionError("Denied input must not be parsed")):
            try:
                connection.putrequest("POST", "/api/rule5/preview")
                connection.putheader("X-SDAD-Session", self.token)
                connection.putheader("Content-Type", "application/json")
                connection.putheader("Content-Length", "2")
                connection.endheaders()
                time.sleep(0.03)
                connection.send(b"{}")
                response = connection.getresponse()
                self.assertEqual(response.status, 403)
                self.assertEqual(json.loads(response.read())["error"]["code"], "invalid_origin")
            finally:
                connection.close()
            action.assert_not_called()
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_authenticated_oversized_delayed_body_returns_413_without_parsing_or_action(self) -> None:
        before = tree_fingerprint(self.project)
        with patch.object(self.server.service, "save_correction") as save, patch.object(self.server.service, "manage_correction") as manage, patch("sdad_inspector.server.json.loads", side_effect=AssertionError("Rejected data must not be parsed")):
            for path, length in (("/api/corrections", 65537), ("/api/corrections/import", 525313)):
                with self.subTest(path=path):
                    connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
                    try:
                        connection.putrequest("POST", path)
                        connection.putheader("Origin", self.server.origin)
                        connection.putheader("X-SDAD-Session", self.token)
                        connection.putheader("Content-Type", "application/json")
                        connection.putheader("Content-Length", str(length))
                        connection.endheaders()
                        time.sleep(0.03)
                        connection.send(b" " * length)
                        response = connection.getresponse()
                        self.assertEqual(response.status, 413)
                        self.assertIn(b"request_too_large", response.read())
                    finally:
                        connection.close()
            save.assert_not_called()
            manage.assert_not_called()
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_authenticated_oversized_missing_body_cannot_hold_connection_open(self) -> None:
        for length in (65537, 131073, 1_000_000_000):
            with self.subTest(length=length):
                connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
                try:
                    connection.putrequest("POST", "/api/corrections")
                    connection.putheader("Origin", self.server.origin)
                    connection.putheader("X-SDAD-Session", self.token)
                    connection.putheader("Content-Type", "application/json")
                    connection.putheader("Content-Length", str(length))
                    started = time.monotonic()
                    connection.endheaders()
                    response = connection.getresponse()
                    self.assertEqual(response.status, 413)
                    response.read()
                    self.assertLess(time.monotonic() - started, 1.5)
                finally:
                    connection.close()

    def test_rejected_incomplete_or_invalid_body_is_time_and_size_bounded(self) -> None:
        for length in ("2", "65537", "invalid", "-1", None):
            with self.subTest(length=length):
                connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
                try:
                    connection.putrequest("POST", "/api/rule5/preview")
                    connection.putheader("X-SDAD-Session", self.token)
                    connection.putheader("Content-Type", "application/json")
                    if length is not None:
                        connection.putheader("Content-Length", length)
                    started = time.monotonic()
                    connection.endheaders()
                    response = connection.getresponse()
                    self.assertEqual(response.status, 403)
                    self.assertEqual(json.loads(response.read())["error"]["code"], "invalid_origin")
                    self.assertLess(time.monotonic() - started, 1.5)
                finally:
                    connection.close()

    def test_index_injects_session_and_sets_browser_security_headers(self) -> None:
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(self.token.encode("ascii"), body)
        self.assertNotIn(b"__SDAD_SESSION_TOKEN__", body)
        self.assertNotIn(b"__SDAD_THEME__", body)
        self.assertNotIn(b"__SDAD_LOCALE__", body)
        self.assertNotIn(b"__SDAD_UI_SCALE__", body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_ui_preferences_are_origin_authenticated_and_injected_on_reopen(self) -> None:
        missing_origin, _, _ = self.request(
            "/api/preferences",
            method="POST",
            token=self.token,
            payload={"theme": "dark", "locale": "zh-CN", "scale": 130},
        )
        self.assertEqual(missing_origin, 403)
        status, _, body = self.request(
            "/api/preferences",
            method="POST",
            token=self.token,
            origin=True,
            payload={"theme": "dark", "locale": "zh-CN", "scale": 130},
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(body),
            {"schema_version": 1, "theme": "dark", "locale": "zh-CN", "scale": 130},
        )
        index_status, _, index_body = self.request("/")
        self.assertEqual(index_status, 200)
        self.assertIn(b'name="sdad-theme" content="dark"', index_body)
        self.assertIn(b'name="sdad-locale" content="zh-CN"', index_body)
        self.assertIn(b'name="sdad-ui-scale" content="130"', index_body)
        self.assertFalse((self.project / "preferences.json").exists())

    def test_startup_without_a_project_keeps_the_api_alive_until_user_selection(self) -> None:
        self.server.service._project_root = None  # noqa: SLF001 - startup state contract
        self.server.service._snapshot = None  # noqa: SLF001 - startup state contract
        status, _, body = self.request("/api/snapshot", token=self.token)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "project_required")
        recent_status, _, _ = self.request("/api/recent-projects", token=self.token)
        self.assertEqual(recent_status, 200)

        open_status, _, open_body = self.request(
            "/api/project",
            method="POST",
            token=self.token,
            origin=True,
            payload={"project_root": str(self.project)},
        )
        self.assertEqual(open_status, 200)
        self.assertEqual(Path(json.loads(open_body)["project"]["root"]), self.project.resolve())

    def test_repository_link_opens_only_the_fixed_official_url(self) -> None:
        with patch("sdad_inspector.server.webbrowser.open", return_value=True) as opener:
            status, _, body = self.request(
                "/api/open-repository",
                method="POST",
                token=self.token,
                origin=True,
                payload={},
            )
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(body)["url"],
            "https://github.com/LiveTrack-X/sdad-inspector",
        )
        opener.assert_called_once_with(
            "https://github.com/LiveTrack-X/sdad-inspector", new=2
        )

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
        by_path = {item["path"]: item for item in documents["documents"]}
        self.assertIn("SPEC/SPEC-COMPLETE.md", by_path)
        self.assertIn("sdad-state.yaml", by_path)
        self.assertIn("version:", by_path["sdad-state.yaml"]["content"])
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

        missing_ack_origin, _, _ = self.request(
            "/api/update/acknowledge",
            method="POST",
            token=self.token,
            payload={},
        )
        self.assertEqual(missing_ack_origin, 403)
        acknowledge_status, _, acknowledge_body = self.request(
            "/api/update/acknowledge",
            method="POST",
            token=self.token,
            origin=True,
            payload={},
        )
        self.assertEqual(acknowledge_status, 200)
        self.assertEqual(json.loads(acknowledge_body)["state"], "unsupported")

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

    def test_failed_rescan_preserves_old_evidence_as_stale_until_successful_recovery(self) -> None:
        previous = self.server.service.snapshot()
        # Large ledgers now expose bounded incomplete previews. A malformed or
        # oversized state contract still fails inspection and must stale the cache.
        todo_path = self.project / "sdad-state.yaml"
        original = todo_path.read_bytes()
        todo_path.write_text(original.decode("utf-8") + "# Additional line\n" * 501, encoding="utf-8")
        changed = tree_fingerprint(self.project)
        status, _, body = self.request("/api/rescan", method="POST", token=self.token, origin=True, payload={})
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "bounded_read_failed")
        self.assertIn("500-line", json.loads(body)["error"]["message"])
        self.assertEqual(self.server.service.progress()["status"], "failed")
        self.assertEqual(tree_fingerprint(self.project), changed)

        status, _, body = self.request("/api/snapshot", token=self.token)
        self.assertEqual(status, 200)
        retained = json.loads(body)
        self.assertEqual(retained, {**previous, "inspection_status": "stale"})
        self.assertEqual(previous["inspection_status"], "completed")
        exported = render_static_report(retained).split("<details>")[0]
        self.assertIn("Doctor Summary — Unavailable", exported)
        self.assertNotIn("0 errors", exported)

        todo_path.write_bytes(original)
        restored = tree_fingerprint(self.project)
        status, _, body = self.request("/api/rescan", method="POST", token=self.token, origin=True, payload={})
        self.assertEqual(status, 200)
        recovered = json.loads(body)
        self.assertEqual(recovered["inspection_status"], "completed")
        self.assertNotEqual(recovered["inspection_id"], previous["inspection_id"])
        self.assertEqual(recovered["doctor"]["exit_code"], 0)
        self.assertEqual(self.server.service.snapshot(), recovered)
        self.assertEqual(tree_fingerprint(self.project), restored)

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
        self.assertEqual(len(records), 1)
        self.assertEqual(Path(records[0]["path"]), self.project.resolve())
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
