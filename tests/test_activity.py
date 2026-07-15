from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from sdad_inspector.activity import MAX_GIT_OUTPUT_BYTES, load_development_activity, parse_commits, parse_porcelain
from sdad_inspector.dialogs import MAX_CLIPBOARD_PATH_CHARS, normalize_clipboard_path
from sdad_inspector.errors import InteractionError
from sdad_inspector.state import load_live_documents

from test_core import WorkspaceCase, tree_fingerprint


class LiveWorkspaceTests(WorkspaceCase):
    def git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.project), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_live_documents_are_limited_to_state_and_declared_evidence_routes(self) -> None:
        (self.project / "secret.md").write_text("# Not routed\n", encoding="utf-8")
        documents = load_live_documents(self.project)
        paths = {item["path"] for item in documents["documents"]}
        self.assertEqual(
            paths,
            {
                "sdad-state.yaml",
                "SPEC/SPEC-COMPLETE.md",
                "docs/TODO-Open-Items.md",
                "review-findings.md",
            },
        )
        self.assertNotIn("secret.md", paths)
        spec = next(item for item in documents["documents"] if item["path"].startswith("SPEC/"))
        self.assertEqual(spec["content"].splitlines(), ["# Fixture SPEC"])
        state = next(item for item in documents["documents"] if item["path"] == "sdad-state.yaml")
        self.assertEqual(state["roles"], ["state"])
        self.assertIn("version: 2", state["content"])

    def test_porcelain_and_commit_parsers_preserve_unicode_without_content_reads(self) -> None:
        unicode_file = self.project / "docs" / "진행.md"
        unicode_file.write_text("work\n", encoding="utf-8")
        output = "?? docs/진행.md\0".encode("utf-8")
        files, truncated = parse_porcelain(self.project, output)
        self.assertFalse(truncated)
        self.assertEqual(files[0]["path"], "docs/진행.md")
        self.assertEqual(files[0]["kind"], "untracked")
        commits = parse_commits(
            b"\x1e0123456789012345678901234567890123456789\x1f0123456\x1f2026-07-15T08:00:00+09:00\x1fbounded subject\n"
        )
        self.assertEqual(commits[0]["subject"], "bounded subject")
        self.assertNotIn("author", commits[0])

        many = b"".join(f"?? docs/{index}.md\0".encode("utf-8") for index in range(161))
        entries, truncated = parse_porcelain(self.project, many)
        self.assertEqual(len(entries), 160)
        self.assertTrue(truncated)

    def test_clipboard_path_is_explicitly_bounded_to_one_value(self) -> None:
        self.assertEqual(normalize_clipboard_path('  "C:\\work\\project"  '), "C:\\work\\project")
        for invalid in ("C:\\one\nC:\\two", "x" * (MAX_CLIPBOARD_PATH_CHARS + 1), "  "):
            with self.subTest(invalid_length=len(invalid)):
                with self.assertRaises(InteractionError):
                    normalize_clipboard_path(invalid)

    def test_activity_reports_status_commits_and_handoff_without_probe_writes(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", ".")
        self.git("commit", "-qm", "Initial SDAD controls")
        (self.project / "SPEC" / "SPEC-COMPLETE.md").write_text(
            "# Fixture SPEC\n\nChanged.\n", encoding="utf-8"
        )
        handoffs = self.project / "docs" / "sdad" / "handoffs"
        handoffs.mkdir(parents=True)
        (handoffs / "2026-07-15-progress.md").write_text(
            "# Progress handoff\n\nContinue the bounded packet.\n", encoding="utf-8"
        )
        before = tree_fingerprint(self.project)
        activity = load_development_activity(self.project)
        after = tree_fingerprint(self.project)
        self.assertEqual(before, after)
        self.assertTrue(activity["available"])
        self.assertEqual(activity["worktree_status"], "changed")
        self.assertIn("SPEC/SPEC-COMPLETE.md", {item["path"] for item in activity["files"]})
        self.assertEqual(activity["commits"][0]["subject"], "Initial SDAD controls")
        self.assertEqual(activity["handoffs"][0]["title"], "Progress handoff")
        self.assertNotIn("author", activity["commits"][0])

    def test_nested_project_limits_status_and_commits_to_its_git_scope(self) -> None:
        repository = self.root / "monorepo"
        project = repository / "packages" / "inspected"
        sibling = repository / "packages" / "sibling"
        shutil.copytree(self.project, project)
        sibling.mkdir(parents=True)
        (sibling / "outside.txt").write_text("initial\n", encoding="utf-8")

        def repo_git(*arguments: str) -> None:
            subprocess.run(
                ["git", "-C", str(repository), *arguments],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        repo_git("init", "-q")
        repo_git("config", "user.name", "Fixture")
        repo_git("config", "user.email", "fixture@example.invalid")
        repo_git("add", ".")
        repo_git("commit", "-qm", "Initial monorepo")
        (project / "SPEC" / "SPEC-COMPLETE.md").write_text(
            "# Nested project\n", encoding="utf-8"
        )
        repo_git("add", "packages/inspected/SPEC/SPEC-COMPLETE.md")
        repo_git("commit", "-qm", "Update inspected project")
        (sibling / "outside.txt").write_text("committed outside\n", encoding="utf-8")
        repo_git("add", "packages/sibling/outside.txt")
        repo_git("commit", "-qm", "Update sibling only")

        (project / ".fixture-note").write_text("inside\n", encoding="utf-8")
        (sibling / "outside.txt").write_text("uncommitted outside\n", encoding="utf-8")
        activity = load_development_activity(project)

        self.assertEqual(Path(activity["project_root"]).resolve(), project.resolve())
        self.assertEqual(Path(activity["git_root"]).resolve(), repository.resolve())
        self.assertEqual(activity["git_scope"], "packages/inspected")
        self.assertEqual({item["path"] for item in activity["files"]}, {".fixture-note"})
        subjects = [item["subject"] for item in activity["commits"]]
        self.assertIn("Update inspected project", subjects)
        self.assertNotIn("Update sibling only", subjects)

    def test_non_git_repository_is_a_recoverable_read_only_state(self) -> None:
        before = tree_fingerprint(self.project)
        activity = load_development_activity(self.project)
        self.assertEqual(tree_fingerprint(self.project), before)
        self.assertFalse(activity["available"])
        self.assertEqual(activity["worktree_status"], "unavailable")
        self.assertEqual(activity["error"]["code"], "not_git_repository")

    def test_clean_repository_and_unicode_rename_are_reported_without_content_reads(self) -> None:
        renamed_from = self.project / "docs" / "old-name.md"
        renamed_to = self.project / "docs" / "새-이름.md"
        renamed_from.write_bytes(b"bounded\r\n")
        system_config = self.root / "git-system-config"
        system_config.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
        with patch.dict(
            os.environ,
            {"GIT_CONFIG_SYSTEM": str(system_config), "GIT_CONFIG_NOSYSTEM": "0"},
        ):
            self.git("init", "-q")
            self.git("config", "user.name", "Fixture")
            self.git("config", "user.email", "fixture@example.invalid")
            self.git("add", ".")
            self.git("commit", "-qm", "Initial clean state")
            clean = load_development_activity(self.project)
            self.assertTrue(clean["available"])
            self.assertEqual(clean["worktree_status"], "clean", clean["files"])
            self.assertEqual(clean["changed_count"], 0)

            self.git("mv", str(renamed_from.relative_to(self.project)), str(renamed_to.relative_to(self.project)))
            changed = load_development_activity(self.project)
            renamed = next(item for item in changed["files"] if item["kind"] == "renamed")
            self.assertEqual(renamed["path"], "docs/새-이름.md")
            self.assertEqual(renamed["previous_path"], "docs/old-name.md")

    def test_unavailable_timeout_and_oversized_git_probes_fail_closed(self) -> None:
        scenarios = (
            (FileNotFoundError("git"), "git_unavailable"),
            (subprocess.TimeoutExpired(["git"], 3), "git_timeout"),
            (
                subprocess.CompletedProcess(
                    args=["git"],
                    returncode=0,
                    stdout=b"x" * (MAX_GIT_OUTPUT_BYTES + 1),
                    stderr=b"",
                ),
                "git_output_limit",
            ),
        )
        for result, expected in scenarios:
            with self.subTest(expected=expected), patch("sdad_inspector.activity.subprocess.run", side_effect=result if isinstance(result, BaseException) else None, return_value=None if isinstance(result, BaseException) else result):
                activity = load_development_activity(self.project)
                self.assertFalse(activity["available"])
                self.assertEqual(activity["error"]["code"], expected)


if __name__ == "__main__":
    import unittest

    unittest.main()
