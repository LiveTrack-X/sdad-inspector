from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sdad_inspector.rule5 import (
    Rule5Error,
    build_rule5_proposal,
    extract_rule5_candidates,
    write_rule5_export,
)
from sdad_inspector.errors import PathSafetyError

from test_core import WorkspaceCase, tree_fingerprint


FINDING = """# Review Findings

## Active Findings

- [Medium] [packet:CORE-1] [FIND-R5-001] The same unsafe action needed a manual warning twice.
  Root cause: The existing flow has no durable boundary check.
  Operational rule: Require the boundary check before the unsafe action.
  Enforcement: A validator rejects the action without the check.
  Regression evidence: tests/test_boundary.py covers allowed and blocked paths.
  Review condition: Keep, Refine, Merge, or Retire after two field uses.

## Recently Closed
"""


class Rule5Tests(WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        (self.project / "review-findings.md").write_text(FINDING, encoding="utf-8")

    def test_extracts_structured_active_finding_and_marks_complete(self) -> None:
        result = extract_rule5_candidates(self.project)
        self.assertEqual(result["source_path"], "review-findings.md")
        self.assertEqual(len(result["source_sha256"]), 64)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["candidate_id"], "R5-FIND-R5-001")
        self.assertEqual(candidate["root_cause"], "The existing flow has no durable boundary check.")
        self.assertIn("validator rejects", candidate["enforcement"])
        self.assertTrue(candidate["complete"])

    def test_preview_is_human_readable_and_export_matches_exact_bytes(self) -> None:
        candidate = extract_rule5_candidates(self.project)["candidates"][0]
        preview = build_rule5_proposal(candidate)
        self.assertIn("# Rule 5 Proposal: R5-FIND-R5-001", preview["markdown"])
        self.assertIn("Status: Candidate - not an active rule", preview["markdown"])
        self.assertIn("## Keep / Refine / Merge / Retire Condition", preview["markdown"])
        before = tree_fingerprint(self.project)
        with tempfile.TemporaryDirectory() as destination:
            saved = write_rule5_export(Path(destination) / "proposal.txt", preview["markdown"])
            self.assertEqual(saved.name, "proposal.md")
            self.assertEqual(saved.read_bytes(), preview["markdown"].encode("utf-8"))
        self.assertEqual(before, tree_fingerprint(self.project))

    def test_incomplete_finding_stays_blocked_instead_of_inventing_a_rule(self) -> None:
        (self.project / "review-findings.md").write_text(
            "# Review Findings\n\n## Active Findings\n\n"
            "- [Low] [packet:CORE-1] [FIND-R5-INCOMPLETE] A repeated failure has no established root cause.\n\n"
            "## Recently Closed\n",
            encoding="utf-8",
        )
        candidate = extract_rule5_candidates(self.project)["candidates"][0]
        self.assertFalse(candidate["complete"])
        self.assertEqual(candidate["root_cause"], "")
        self.assertEqual(candidate["operational_rule"], "")
        with self.assertRaises(Rule5Error):
            build_rule5_proposal(candidate)

    def test_export_cannot_write_into_the_inspected_repository(self) -> None:
        candidate = extract_rule5_candidates(self.project)["candidates"][0]
        preview = build_rule5_proposal(candidate)
        destination = self.project / "rules" / "proposal.md"
        destination.parent.mkdir()
        before = tree_fingerprint(self.project)
        with self.assertRaises(PathSafetyError):
            write_rule5_export(
                destination,
                preview["markdown"],
                forbidden_root=self.project,
            )
        self.assertFalse(destination.exists())
        self.assertEqual(before, tree_fingerprint(self.project))


if __name__ == "__main__":
    unittest.main()
