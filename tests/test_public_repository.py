from __future__ import annotations

import unittest
from pathlib import PurePosixPath

from scripts.validate_public_repository import audit_bytes


class PublicRepositoryAuditTests(unittest.TestCase):
    def test_accepts_repository_relative_public_text(self) -> None:
        self.assertEqual(
            audit_bytes(PurePosixPath("docs/guide.md"), b"Public product documentation."),
            [],
        )

    def test_rejects_private_sdad_control_plane(self) -> None:
        private_paths = (
            "AGENTS.md",
            "web/AGENTS.md",
            "sdad-state.yaml",
            "review-findings.md",
            "SDAD_INSPECTOR_PRODUCT_PLAN.md",
            "SPEC/SPEC-COMPLETE.md",
            "design/reference/concept.png",
            "docs/INDEX.md",
            "docs/TODO-Open-Items.md",
            "docs/evidence-matrix.md",
            "docs/OWNER_DECISIONS.md",
            "docs/work-packet-state.md",
            "docs/sdad/playbooks/work-packets.md",
        )
        for raw_path in private_paths:
            path = PurePosixPath(raw_path)
            with self.subTest(path=raw_path):
                self.assertIn(
                    f"{path}: private SDAD control-plane path is included",
                    audit_bytes(path, b"local-only control"),
                )

    def test_allows_synthetic_sdad_compatibility_fixture(self) -> None:
        self.assertEqual(
            audit_bytes(
                PurePosixPath("tests/fixture-projects/state-v2/sdad-state.yaml"),
                b"version: 2\n",
            ),
            [],
        )

    def test_rejects_personal_absolute_path(self) -> None:
        content = ("C:" + "\\Users\\owner\\private\\capture.png").encode()
        self.assertIn(
            "docs/qa.md: contains a personal absolute path",
            audit_bytes(PurePosixPath("docs/qa.md"), content),
        )

    def test_allows_declared_operating_system_path_fixture(self) -> None:
        content = ("C:" + "\\Users\\owner\\AppData\\Local").encode()
        self.assertEqual(
            audit_bytes(PurePosixPath("tests/test_preferences.py"), content),
            [],
        )

    def test_rejects_high_confidence_github_token(self) -> None:
        content = ("ghp_" + "a" * 40).encode()
        self.assertIn(
            "notes.txt: contains a GitHub token",
            audit_bytes(PurePosixPath("notes.txt"), content),
        )

    def test_rejects_sensitive_filename_and_generated_directory(self) -> None:
        self.assertTrue(audit_bytes(PurePosixPath(".env.local"), b"placeholder"))
        self.assertTrue(audit_bytes(PurePosixPath("web/.npmrc"), b"placeholder"))
        self.assertTrue(audit_bytes(PurePosixPath("build/output.txt"), b"placeholder"))

    def test_rejects_historical_qa_and_local_machine_files(self) -> None:
        self.assertTrue(
            audit_bytes(PurePosixPath("design/qa/capture.png"), b"not-a-real-png")
        )
        self.assertTrue(audit_bytes(PurePosixPath("design-qa.md"), b"local ledger"))
        self.assertTrue(audit_bytes(PurePosixPath(".DS_Store"), b"metadata"))


if __name__ == "__main__":
    unittest.main()
