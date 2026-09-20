from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import release_candidate as candidate
from scripts import release_metadata as metadata
from scripts.release_metadata import ROOT, VERSION, TAG, WINDOWS_VERSION, windows_resource


class CandidateIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.identity = candidate.identity("a" * 40, VERSION, "owner/repo", "123", "2")
        for name in candidate.archive_names(VERSION):
            (self.root / name).write_bytes(name.encode())
        candidate.create(self.root, self.identity)

    def test_exact_candidate_and_same_tag_verify_without_writes(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        candidate.verify(self.root, self.identity, TAG)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        with self.assertRaises(ValueError):
            candidate.create(self.root, self.identity)

    def test_wrong_commit_version_repository_run_attempt_or_tag_is_rejected(self):
        for key, value in (("commit", "b" * 40), ("version", "99.0.0"),
                           ("repository", "other/repo"), ("run_id", "456"), ("run_attempt", "3")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate.verify(self.root, {**self.identity, key: value}, TAG)
        with self.assertRaises(ValueError):
            candidate.verify(self.root, self.identity, "v99.0.0")

    def test_changed_bytes_size_missing_or_extra_archive_fail(self):
        archive = self.root / sorted(candidate.archive_names(VERSION))[0]
        original = archive.read_bytes()
        for payload in (b"x" * len(original), original + b"x"):
            archive.write_bytes(payload)
            with self.assertRaises(ValueError):
                candidate.verify(self.root, self.identity, TAG)
        archive.unlink()
        with self.assertRaises(ValueError):
            candidate.verify(self.root, self.identity, TAG)
        archive.write_bytes(original)
        (self.root / "unexpected.zip").write_bytes(b"extra")
        with self.assertRaises(ValueError):
            candidate.verify(self.root, self.identity, TAG)

    def test_manifest_tampering_and_path_escape_are_rejected(self):
        path = self.root / candidate.MANIFEST
        manifest = json.loads(path.read_text())
        for change in ({"commit": "b" * 40}, {"archives": [{"name": "../escape"}]},
                       {"schema_version": 2}, {"schema_version": True}, {"extra": "unknown"}):
            path.write_text(json.dumps({**manifest, **change}))
            with self.assertRaises(ValueError):
                candidate.verify(self.root, self.identity, TAG)
        path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):
            candidate.verify(self.root, self.identity, TAG)

    def test_untrusted_failed_incomplete_wrong_branch_or_workflow_runs_fail(self):
        good = {"conclusion": "success", "status": "completed", "head_sha": "a" * 40,
                "head_branch": "main", "event": "push", "path": candidate.WORKFLOW,
                "repository": {"full_name": "owner/repo"}, "head_repository": {"full_name": "owner/repo"}}
        candidate.validate_run(good, "owner/repo", "a" * 40)
        for key, value in (("conclusion", "failure"), ("status", "in_progress"),
                           ("head_sha", "b" * 40), ("head_branch", "feature"),
                           ("event", "pull_request"), ("path", "other.yml"),
                           ("head_repository", {"full_name": "fork/repo"}),
                           ("repository", {"full_name": "other/repo"})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate.validate_run({**good, key: value}, "owner/repo", "a" * 40)

    def test_remote_tag_peels_but_never_moves_or_recreates_tags(self):
        with patch.object(candidate, "api", side_effect=[
            {"object": {"type": "tag", "sha": "c" * 40}},
            {"object": {"type": "commit", "sha": "a" * 40}},
        ]) as api:
            candidate.check_remote_tag("owner/repo", TAG, "a" * 40)
            self.assertEqual(api.call_count, 2)
        with patch.object(candidate, "api", return_value={"object": {"type": "commit", "sha": "b" * 40}}):
            with self.assertRaises(ValueError):
                candidate.check_remote_tag("owner/repo", TAG, "a" * 40)


class ReleaseAuthorityTests(unittest.TestCase):
    def test_metadata_sync_can_retry_partial_readme_failure_without_losing_old_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "packaging").mkdir()
            resource = root / "packaging/sdad-inspector-version.txt"
            resource.write_text("ProductVersion', '0.0.3'")
            (root / "packaging/sdad-inspector-version.txt.in").write_text("ProductVersion', '@PRODUCT_VERSION@'")
            for name in ("README.md", "README.ko.md", "README.ja.md", "README.zh-CN.md"):
                (root / name).write_text("Download 0.0.3; historical 0.0.1")
            original_write = Path.write_text
            def fail_second_readme(path, *args, **kwargs):
                if path.name == "README.ko.md":
                    raise OSError("simulated failed guide write")
                return original_write(path, *args, **kwargs)
            with patch.object(metadata, "ROOT", root), patch("sys.argv", ["release_metadata.py", "--sync"]):
                with patch.object(Path, "write_text", fail_second_readme), self.assertRaises(OSError):
                    metadata.main()
                self.assertIn("0.0.3", resource.read_text())
                metadata.main()
            for name in ("README.md", "README.ko.md", "README.ja.md", "README.zh-CN.md"):
                self.assertEqual((root / name).read_text(), f"Download {VERSION}; historical 0.0.1")
            self.assertIn(VERSION, resource.read_text())

    def test_runtime_package_and_windows_resource_share_authority(self):
        from sdad_inspector import __version__
        self.assertEqual(__version__, VERSION)
        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn('version = {attr = "sdad_inspector.version.__version__"}', pyproject)
        self.assertNotIn(f'version = "{VERSION}"', pyproject)
        self.assertEqual((ROOT / "packaging/sdad-inspector-version.txt").read_text(), windows_resource())
        self.assertIn(f"filevers={WINDOWS_VERSION}", windows_resource())
        self.assertIn(f"prodvers={WINDOWS_VERSION}", windows_resource())

    def test_candidate_and_promotion_keep_gates_without_rebuilding_or_moving_tags(self):
        workflow = yaml.load((ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader)
        ci = yaml.load((ROOT / candidate.WORKFLOW).read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(ci["on"]["push"], {"branches": ["**"]})
        self.assertIn("pull_request", ci["on"])
        self.assertIn("workflow_dispatch", ci["on"])
        self.assertEqual(ci["jobs"]["candidate"]["needs"], ["preview", "portable-smoke"])
        self.assertEqual(ci["jobs"]["candidate"]["if"], "github.event_name == 'push' && github.ref == 'refs/heads/main'")
        self.assertEqual(workflow["jobs"]["release"]["needs"], ["candidate", "portable-smoke"])
        self.assertEqual(workflow["permissions"]["contents"], "read")
        self.assertEqual(workflow["jobs"]["release"]["permissions"]["attestations"], "write")
        for job in ("portable-smoke", "release"):
            steps = workflow["jobs"][job]["steps"]
            download = next(s for s in steps if s.get("uses", "").startswith("actions/download-artifact@"))
            self.assertEqual(download["with"]["run-id"], "${{ needs.candidate.outputs.run_id }}")
            self.assertEqual(download["with"]["name"], "verified-release-candidate")
            commands = "\n".join(s.get("run", "") for s in steps)
            self.assertIn("release_candidate.py verify", commands)
            self.assertNotIn("build_native.py", commands)
            self.assertNotIn("git push", commands)
            self.assertNotIn("--clobber", commands)
        publication = "\n".join(s.get("run", "") for s in workflow["jobs"]["release"]["steps"])
        self.assertIn("release_candidate.py remote-check", publication)
        self.assertIn('gh release view "$GITHUB_REF_NAME"', publication)
        self.assertIn("--verify-tag", publication)
        self.assertIn("--draft=false", publication)


if __name__ == "__main__":
    unittest.main()
