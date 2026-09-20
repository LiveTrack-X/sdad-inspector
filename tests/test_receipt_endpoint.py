"""Receipt projection is an explicit, project-bound read, never an execution API."""
import json
import unittest
from unittest.mock import patch

import yaml

from test_server import LoopbackServerTests
from test_core import tree_fingerprint
from test_receipts import fixture_receipt


class ReceiptEndpointTests(LoopbackServerTests):
    # Reuse the real server fixture; load_tests selects the new regression only.
    def setUp(self):
        super().setUp()
        # The renderer sends the service's canonical project identity. macOS
        # temporary paths may arrive through /var -> /private/var aliases.
        self.project = self.server.service.project_root

    def test_receipt_read_requires_session_origin_and_selected_project(self):
        before = tree_fingerprint(self.project)
        payload = {"project_root": str(self.project)}
        with patch("sdad_inspector.receipts.load_verification_receipts") as read:
            read.return_value = {"project_root": str(self.project), "packet": "P1", "read_at": "2026-09-20T00:00:00Z", "receipts": [], "truncated": False}
            status, _, _ = self.request("/api/verification-receipts", method="POST", payload=payload)
            self.assertEqual(status, 403)
            read.assert_not_called()
            status, _, _ = self.request("/api/verification-receipts", method="POST", token=self.token, origin=True, payload={"project_root": "other"})
            self.assertEqual(status, 422)
            read.assert_not_called()
            status, _, body = self.request("/api/verification-receipts", method="POST", token=self.token, origin=True, payload=payload)
            self.assertEqual(status, 200, body)
            self.assertEqual(json.loads(body)["receipts"], [])
            read.assert_called_once_with(self.project)
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_resume_api_is_project_and_inspection_bound_and_preserves_project(self):
        before = tree_fingerprint(self.project)
        snapshot = self.server.service.snapshot()
        payload = {"project_root": str(self.project), "inspection_id": snapshot["inspection_id"], "action": "enable"}
        for overrides in ({"action": []}, {"action": {}}, {"inspection_id": "old"}, {"project_root": "other"}):
            status, _, _ = self.request("/api/resume-comparison", method="POST", token=self.token, origin=True, payload={**payload, **overrides})
            self.assertEqual(status, 422)
        status, _, body = self.request("/api/resume-comparison", method="POST", token=self.token, origin=True, payload=payload)
        self.assertEqual(status, 200, body)
        data = json.loads(body)
        self.assertEqual(data["projects"][0]["baseline"]["inspectionId"], snapshot["inspection_id"])
        self.assertEqual(data["retained_projects"], 1)
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_receipt_navigation_authentication_and_project_binding_precede_reads(self):
        endpoints = (("list", "list_verification_receipts"), ("inspect", "inspect_verification_receipt"))
        before = tree_fingerprint(self.project)
        for suffix, function in endpoints:
            path = f"/api/verification-receipt-{suffix}"
            with self.subTest(suffix=suffix), patch(f"sdad_inspector.receipts.{function}") as read:
                for token, origin in ((None, False), (self.token, False), (None, True)):
                    status, _, _ = self.request(path, method="POST", token=token, origin=origin, payload={"project_root": str(self.project)})
                    self.assertEqual(status, 403)
                status, _, body = self.request(path, method="POST", token=self.token, origin=True, payload={"project_root": "other"})
                self.assertEqual(status, 422)
                self.assertEqual(json.loads(body)["error"]["code"], "receipt_navigation_project")
                read.assert_not_called()
        self.assertEqual(tree_fingerprint(self.project), before)

    def test_receipt_navigation_http_pages_selected_read_and_stale_revision(self):
        state_path = self.project / "sdad-state.yaml"
        state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        state["routed_docs"] = [f"missing-{i}.json" for i in range(10)] + ["receipt.json"]
        state_path.write_text(yaml.safe_dump(state), encoding="utf-8")
        (self.project / "receipt.json").write_text(json.dumps(fixture_receipt()), encoding="utf-8")
        (self.project / "source.py").write_bytes(b"source")
        (self.project / "receipt.json.log").write_bytes(b"ok")
        before = tree_fingerprint(self.project)

        def post(suffix, **payload):
            status, _, body = self.request(f"/api/verification-receipt-{suffix}", method="POST", token=self.token,
                                           origin=True, payload={"project_root": str(self.project), **payload})
            return status, json.loads(body)

        status, page = post("list")
        self.assertEqual(status, 200, page)
        self.assertEqual((page["total"], page["next_offset"]), (11, 10))
        status, last = post("list", offset=10, revision=page["revision"])
        self.assertEqual(status, 200, last)
        self.assertEqual(last["paths"], ["receipt.json"])
        status, result = post("inspect", path="receipt.json", revision=last["revision"])
        self.assertEqual(status, 200, result)
        self.assertEqual(result["observation"]["source_match"], "matched")
        self.assertEqual(result["observation"]["receipt"]["packet"], "P1")
        for suffix, extra in (("list", {"offset": True}), ("inspect", {"path": "../receipt.json", "revision": page["revision"]})):
            status, result = post(suffix, **extra)
            self.assertEqual(status, 422)
            self.assertEqual(result["error"]["code"], "receipt_navigation_invalid")
        self.assertEqual(before, tree_fingerprint(self.project))
        state["active_packet"]["id"] = "NEW"
        state_path.write_text(yaml.safe_dump(state), encoding="utf-8")
        for suffix, extra in (("list", {"offset": 10}), ("inspect", {"path": "receipt.json"})):
            status, result = post(suffix, revision=page["revision"], **extra)
            self.assertEqual(status, 422)
            self.assertEqual(result["error"]["code"], "receipt_navigation_changed")


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        ReceiptEndpointTests("test_receipt_read_requires_session_origin_and_selected_project")
        , ReceiptEndpointTests("test_resume_api_is_project_and_inspection_bound_and_preserves_project")
        , ReceiptEndpointTests("test_receipt_navigation_authentication_and_project_binding_precede_reads")
        , ReceiptEndpointTests("test_receipt_navigation_http_pages_selected_read_and_stale_revision")
    ])
