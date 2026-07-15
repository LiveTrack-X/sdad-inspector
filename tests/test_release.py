from __future__ import annotations

import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from sdad_inspector.errors import PackageError
from scripts.build_native import require_release_python
from scripts.package_release import build_release_archive, normalized_architecture
from scripts.smoke_release_archive import extract_single_executable
from scripts.write_checksums import write_checksums


class ReleasePackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="sdad-inspector-release-")
        self.root = Path(self.temporary.name)
        self.dist = self.root / "dist"
        self.output = self.root / "release-artifacts"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_windows_archive_has_stable_name_root_and_hash(self) -> None:
        self.dist.mkdir(parents=True)
        (self.dist / "SDAD-Inspector.exe").write_bytes(b"binary")

        evidence = build_release_archive(
            dist_root=self.dist,
            output_dir=self.output,
            platform_name="windows",
            version="0.0.2",
            architecture="X64",
        )

        archive = Path(str(evidence["archive"]))
        self.assertEqual(
            archive.name, "SDAD-Inspector-0.0.2-windows-x64.zip"
        )
        self.assertEqual(len(str(evidence["sha256"])), 64)
        self.assertTrue(evidence["unsigned"])
        self.assertEqual(evidence["archive_member_count"], 1)
        self.assertEqual(evidence["package_mode"], "unsigned-one-file-portable")
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.namelist(), ["SDAD-Inspector.exe"])

        extracted = extract_single_executable(
            archive, self.root / "extracted-windows", "windows"
        )
        self.assertEqual(extracted.read_bytes(), b"binary")
        self.assertEqual(
            [path.name for path in extracted.parent.iterdir()], ["SDAD-Inspector.exe"]
        )

    def test_macos_archive_contains_one_portable_executable(self) -> None:
        executable = self.dist / "SDAD-Inspector"
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"binary")

        evidence = build_release_archive(
            dist_root=self.dist,
            output_dir=self.output,
            platform_name="macos",
            version="0.0.2",
            architecture="ARM64",
        )

        archive = Path(str(evidence["archive"]))
        self.assertEqual(
            archive.name, "SDAD-Inspector-0.0.2-macos-arm64.tar.gz"
        )
        with tarfile.open(archive, "r:gz") as bundled:
            self.assertEqual(bundled.getnames(), ["SDAD-Inspector"])

    def test_portable_build_runtime_is_pinned_to_cpython_312(self) -> None:
        evidence = require_release_python(
            implementation="cpython",
            version=(3, 12),
            executable="python",
        )
        self.assertEqual(evidence["python_version"], "3.12")
        with self.assertRaises(PackageError):
            require_release_python(
                implementation="cpython",
                version=(3, 13),
                executable="python",
            )

    def test_checksum_manifest_requires_one_archive_per_platform(self) -> None:
        self.output.mkdir(parents=True)
        for name in (
            "SDAD-Inspector-0.0.2-linux-x64.tar.gz",
            "SDAD-Inspector-0.0.2-macos-arm64.tar.gz",
            "SDAD-Inspector-0.0.2-windows-x64.zip",
        ):
            (self.output / name).write_text(name, encoding="utf-8")

        evidence = write_checksums(self.output)

        manifest = (self.output / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertEqual(evidence["count"], 3)
        self.assertEqual(len(manifest.splitlines()), 3)
        self.assertIn("windows-x64.zip", manifest)

    def test_architecture_aliases_are_explicit(self) -> None:
        self.assertEqual(normalized_architecture("AMD64"), "x64")
        self.assertEqual(normalized_architecture("aarch64"), "arm64")
        with self.assertRaises(ValueError):
            normalized_architecture("unknown")


if __name__ == "__main__":
    unittest.main()
