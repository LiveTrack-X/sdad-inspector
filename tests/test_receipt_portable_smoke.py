from __future__ import annotations

import importlib.util
from pathlib import Path
import threading
from urllib.error import HTTPError

from sdad_inspector.preferences import RecentProjectsStore
from sdad_inspector.server import InspectorService, create_server
from test_core import WorkspaceCase, tree_fingerprint


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "receipt_portable_smoke.py"
spec = importlib.util.spec_from_file_location("receipt_portable_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class ReceiptPortableSmokeTests(WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = (self.root / "portable receipt fixture").resolve()
        smoke.fixture(self.project)
        self.before = tree_fingerprint(self.project)
        web = self.root / "portable-web"
        web.mkdir()
        (web / "index.html").write_text('<!doctype html><meta name="sdad-session" content="__SDAD_SESSION_TOKEN__"><div id="root"></div>', encoding="utf-8")
        service = InspectorService(self.project, self.engine, engine_info=self.engine_info,
                                   preferences_store=RecentProjectsStore(self.root / "portable-app" / "preferences.json"))
        self.token = "portable-receipt-authenticated-test"
        self.server = create_server(service, web, session_token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def test_helper_uses_real_authenticated_api_and_leaves_fixture_unchanged(self) -> None:
        checks = smoke.check_api(self.server.origin, self.project, self.token)
        self.assertEqual(checks, ["completed_project_observation", "first_page_10_of_11", "malformed_receipt_rejected", "eleventh_receipt_source_and_log_match"])
        self.assertEqual(tree_fingerprint(self.project), self.before)
        self.assertEqual(len(list((self.project / "evidence").glob("*.json"))), 11)

    def test_tampered_source_fails_smoke_instead_of_reporting_package_success(self) -> None:
        (self.project / "source.txt").write_bytes(b"tampered after receipt")
        changed = tree_fingerprint(self.project)
        with self.assertRaisesRegex(ValueError, "does not match its fixture"):
            smoke.check_api(self.server.origin, self.project, self.token)
        self.assertEqual(tree_fingerprint(self.project), changed)

    def test_wrong_session_token_is_rejected_by_real_api(self) -> None:
        with self.assertRaises(HTTPError) as caught:
            smoke.check_api(self.server.origin, self.project, "wrong-session")
        self.assertEqual(caught.exception.code, 403)
        self.assertEqual(tree_fingerprint(self.project), self.before)
