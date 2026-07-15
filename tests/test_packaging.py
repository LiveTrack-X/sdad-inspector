from __future__ import annotations

import json
from unittest.mock import patch

from sdad_inspector.engine import RELEASE_TREE_SHA256, _release_tree_digest, probe_engine
from sdad_inspector.errors import EngineError, PackageError
from sdad_inspector.packaging import stage_release_engine

from test_core import WorkspaceCase


class EngineStagingTests(WorkspaceCase):
    def test_authenticated_release_is_copied_and_reauthenticated(self) -> None:
        digest = _release_tree_digest(self.engine)
        destination = self.root / "staged-engine"
        with patch.dict(RELEASE_TREE_SHA256, {"3.2.2": digest}):
            staged = stage_release_engine(self.engine, destination)
            reprobe = probe_engine(destination)
            reused = stage_release_engine(self.engine, destination)
        self.assertFalse(staged.reused)
        self.assertTrue(reused.reused)
        self.assertEqual(staged.tree_sha256, digest)
        self.assertEqual(reprobe.revision, self.engine_info.revision)
        marker = json.loads(
            (destination / ".sdad-release.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marker["tree_sha256"], digest)
        self.assertFalse((destination / ".git").exists())
        self.assertEqual(list(destination.rglob("__pycache__")), [])
        self.assertEqual(list(destination.rglob("*.pyc")), [])

    def test_runtime_artifacts_make_an_existing_stage_non_reusable(self) -> None:
        digest = _release_tree_digest(self.engine)
        destination = self.root / "staged-engine"
        with patch.dict(RELEASE_TREE_SHA256, {"3.2.2": digest}):
            stage_release_engine(self.engine, destination)
            cache = destination / "scripts" / "__pycache__"
            cache.mkdir()
            (cache / "sdad.pyc").write_bytes(b"runtime")
            with self.assertRaises(PackageError):
                stage_release_engine(self.engine, destination)

    def test_existing_unauthenticated_destination_is_never_overwritten(self) -> None:
        digest = _release_tree_digest(self.engine)
        destination = self.root / "staged-engine"
        destination.mkdir()
        sentinel = destination / "owner-file.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        with patch.dict(RELEASE_TREE_SHA256, {"3.2.2": digest}):
            with self.assertRaises(PackageError):
                stage_release_engine(self.engine, destination)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_failed_source_authentication_creates_no_destination(self) -> None:
        destination = self.root / "staged-engine"
        with patch(
            "sdad_inspector.packaging.probe_engine",
            side_effect=EngineError("untrusted source"),
        ):
            with self.assertRaises(EngineError):
                stage_release_engine(self.engine, destination)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    import unittest

    unittest.main()
