"""Bounded path navigation does not grant execution or source-read authority."""
from __future__ import annotations

import copy
import hashlib
import json
from unittest.mock import patch

import yaml

from sdad_inspector import receipts
from sdad_inspector.receipts import ReceiptNavigationError, inspect_verification_receipt, list_verification_receipts
from test_core import WorkspaceCase, tree_fingerprint
from test_receipts import fixture_receipt


class ReceiptNavigationTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.value = fixture_receipt()
        (self.project / "source.py").write_bytes(b"source")
        (self.project / "receipt.json.log").write_bytes(b"ok")
        self.write_receipt("receipt.json")
        self.set_routes(["receipt.json"])

    def write_receipt(self, path, value=None):
        (self.project / path).write_text(json.dumps(self.value if value is None else value), encoding="utf-8")

    def set_routes(self, paths, packet="CURRENT"):
        path = self.project / "sdad-state.yaml"
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        value["routed_docs"] = paths
        value["active_packet"]["id"] = packet
        path.write_text(yaml.safe_dump(value), encoding="utf-8")

    def inspect(self, path="receipt.json", revision=None):
        if revision is None:
            revision = list_verification_receipts(self.project)["revision"]
        return inspect_verification_receipt(self.project, path=path, revision=revision)

    def assert_error(self, code, operation):
        with self.assertRaises(ReceiptNavigationError) as raised:
            operation()
        self.assertEqual(raised.exception.code, code)

    def test_all_registered_paths_reachable_without_reading_receipts_sources_or_ledgers(self):
        routes = [f"receipt-{i}.json" for i in range(23)]
        self.set_routes(routes + ["docs/TODO-Open-Items.md", routes[0]])
        before = tree_fingerprint(self.project)
        read = receipts._read

        def state_only(root, path, maximum):
            self.assertEqual(path, "sdad-state.yaml")
            return read(root, path, maximum)

        with patch.object(receipts, "_read", side_effect=state_only), patch.object(receipts, "load_control_state", side_effect=AssertionError("must not load ledgers")), patch("subprocess.Popen", side_effect=AssertionError("must not execute")):
            first = list_verification_receipts(self.project)
            second = list_verification_receipts(self.project, offset=first["next_offset"], revision=first["revision"])
            third = list_verification_receipts(self.project, offset=second["next_offset"], revision=second["revision"])
        self.assertEqual(first["version"], 1)
        self.assertEqual(first["total"], 23)
        self.assertEqual(first["packet"], "CURRENT")
        self.assertEqual(first["project_root"], str(self.project.resolve()))
        self.assertEqual([len(page["paths"]) for page in (first, second, third)], [10, 10, 3])
        self.assertEqual(first["paths"] + second["paths"] + third["paths"], routes)
        self.assertIsNone(third["next_offset"])
        self.assertEqual(before, tree_fingerprint(self.project))

    def test_record_after_malformed_and_oversized_first_ten_is_independently_inspected(self):
        paths = [f"bad-{i}.json" for i in range(10)]
        for path in paths:
            (self.project / path).write_bytes(b"x" * (receipts.MAX_RECEIPT_BYTES + 1) if path == paths[0] else b"{")
        self.set_routes(paths + ["receipt.json"])
        page = list_verification_receipts(self.project)
        read = receipts._read
        observed = []

        def selected_only(root, path, maximum):
            observed.append(path)
            self.assertNotIn(path, paths)
            return read(root, path, maximum)

        before = tree_fingerprint(self.project)
        with patch.object(receipts, "_read", side_effect=selected_only):
            result = self.inspect(revision=page["revision"])
        self.assertEqual(result["packet"], "CURRENT")
        self.assertEqual(result["observation"]["receipt"]["packet"], "P1")
        self.assertEqual(result["observation"]["source_match"], "matched")
        self.assertEqual(result["observation"]["log_match"], "matched")
        self.assertIn("source.py", observed)
        self.assertEqual(before, tree_fingerprint(self.project))

    def test_selected_record_has_its_own_real_16_mib_source_budget(self):
        large = copy.deepcopy(self.value)
        data = b"s" * receipts.MAX_SOURCE_BYTES
        identity = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        large["sources"] = []
        for index in range(8):
            path = f"large-{index}.py"
            (self.project / path).write_bytes(data)
            large["sources"].append({"path": path, "before": identity, "after": identity, "error": None})
        large["sources"].append(self.value["sources"][0])
        self.write_receipt("large.json", large)
        self.set_routes(["large.json", "receipt.json"])
        first = self.inspect("large.json")["observation"]
        self.assertEqual([source["match"] for source in first["sources"]], ["matched"] * 8 + ["unknown"])
        selected = self.inspect()["observation"]
        self.assertEqual(selected["source_match"], "matched")
        self.assertEqual(selected["sources"][0]["reason"], "declared_bytes_match")
        self.assertEqual(receipts.MAX_TOTAL_SOURCE_BYTES, 16 * 1024 * 1024)

    def test_failed_reads_consume_allowance_instead_of_exceeding_total_budget(self):
        value = copy.deepcopy(self.value)
        value["sources"] = [{**copy.deepcopy(value["sources"][0]), "path": f"missing-{i}.py"} for i in range(9)]
        self.write_receipt("receipt.json", value)
        read = receipts._read
        observed = []

        def fail_after_read(root, path, maximum):
            if path.startswith("missing-"):
                observed.append(path)
                raise ValueError("Source changed after reading its allowance")
            return read(root, path, maximum)

        with patch.object(receipts, "_read", side_effect=fail_after_read):
            result = self.inspect()["observation"]
        self.assertEqual(len(observed), 8)
        self.assertEqual(result["source_match"], "unknown")

    def test_route_packet_or_any_state_change_invalidates_continuation_and_selection(self):
        for change in ("routes", "packet", "comment"):
            with self.subTest(change=change):
                self.set_routes(["receipt.json"] + [f"other-{i}.json" for i in range(12)])
                previous = list_verification_receipts(self.project)
                if change == "routes":
                    self.set_routes(["receipt.json", "new.json"])
                elif change == "packet":
                    self.set_routes(previous["paths"], packet="NEW")
                else:
                    with (self.project / "sdad-state.yaml").open("a", encoding="utf-8") as stream:
                        stream.write("\n# changed declaration\n")
                self.assert_error("receipt_navigation_changed", lambda: list_verification_receipts(self.project, offset=10, revision=previous["revision"]))
                self.assert_error("receipt_navigation_changed", lambda: self.inspect(revision=previous["revision"]))

    def test_route_change_during_comparison_discards_observation(self):
        revision = list_verification_receipts(self.project)["revision"]
        read = receipts._read

        def change_routes(root, path, maximum):
            data = read(root, path, maximum)
            if path == "source.py":
                self.set_routes(["different.json"])
            return data

        with patch.object(receipts, "_read", side_effect=change_routes):
            self.assert_error("receipt_navigation_changed", lambda: self.inspect(revision=revision))

    def test_changed_source_and_malformed_selected_receipt_retain_honest_observations(self):
        revision = list_verification_receipts(self.project)["revision"]
        (self.project / "source.py").write_bytes(b"edited")
        result = self.inspect(revision=revision)["observation"]
        self.assertEqual(result["source_match"], "changed")
        self.assertEqual(result["receipt"]["outcome"], "passed")
        (self.project / "receipt.json").write_bytes(b"{")
        result = self.inspect(revision=revision)["observation"]
        self.assertIsNone(result["receipt"])
        self.assertEqual(result["source_match"], "unknown")
        self.assertTrue(result["error"])

    def test_unsafe_and_unregistered_paths_rejected_without_evidence_reads(self):
        unsafe = ["../receipt.json", "C:/receipt.json", ".git/receipt.json", ".env/receipt.json", "credentials.json", "CON.json", "dir./receipt.json", "receipt\\file.json"]
        self.set_routes(["receipt.json"] + unsafe)
        page = list_verification_receipts(self.project)
        self.assertEqual(page["paths"], ["receipt.json"])
        with patch.object(receipts, "_inspect_receipt", side_effect=AssertionError("no evidence read")):
            for path in unsafe + [None, {}, 5, "source.py"]:
                self.assert_error("receipt_navigation_invalid", lambda: self.inspect(path, page["revision"]))
            self.assert_error("receipt_navigation_unregistered", lambda: self.inspect("other.json", page["revision"]))

    def test_offsets_revisions_and_missing_or_malformed_state_fail_explicitly(self):
        for offset in (True, -1, 0.5, "1", None, {}):
            self.assert_error("receipt_navigation_invalid", lambda: list_verification_receipts(self.project, offset=offset))
        for revision in (True, 4, "bad", {}, []):
            self.assert_error("receipt_navigation_invalid", lambda: list_verification_receipts(self.project, revision=revision))
        self.assert_error("receipt_navigation_invalid", lambda: list_verification_receipts(self.project, offset=1))
        revision = list_verification_receipts(self.project)["revision"]
        self.assert_error("receipt_navigation_invalid", lambda: list_verification_receipts(self.project, offset=2, revision=revision))
        self.assert_error("receipt_navigation_invalid", lambda: inspect_verification_receipt(self.project, path="receipt.json", revision=None))
        for data in ("[", "version: 99", "version: 2\nactive_packet: []", "version: 2\nactive_packet: {id: P}\nrouted_docs: {}", "# comment\n" * 501, "x" * (receipts.MAX_CONTROL_BYTES + 1)):
            (self.project / "sdad-state.yaml").write_text(data, encoding="utf-8")
            self.assert_error("receipt_navigation_unavailable", lambda: list_verification_receipts(self.project))
        (self.project / "sdad-state.yaml").unlink()
        self.assert_error("receipt_navigation_unavailable", lambda: list_verification_receipts(self.project))

    def test_revision_is_bound_to_project_even_for_identical_state(self):
        revision = list_verification_receipts(self.project)["revision"]
        other = self.project.parent / "other-project"
        other.mkdir()
        (other / "sdad-state.yaml").write_bytes((self.project / "sdad-state.yaml").read_bytes())
        self.assert_error("receipt_navigation_changed", lambda: list_verification_receipts(other, revision=revision))
        self.assert_error("receipt_navigation_changed", lambda: inspect_verification_receipt(other, path="receipt.json", revision=revision))
