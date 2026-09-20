from __future__ import annotations

import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from sdad_inspector.errors import PackageError
from scripts.build_native import require_release_python, resolve_npm_executable
from scripts.package_release import build_release_archive, normalized_architecture
from scripts.smoke_release_archive import extract_single_executable
from scripts.write_checksums import write_checksums
from scripts import validate_release as release_contract
from scripts.release_metadata import VERSION, SOURCE_START, SOURCE_END, source_version_block


class ReleaseDocumentationContractTests(unittest.TestCase):
    def test_source_candidate_does_not_require_published_release_claim(self) -> None:
        read = release_contract._read
        def candidate_copy(relative: str) -> str:
            text = read(relative)
            if relative.startswith("README"):
                text = text.replace(f"{VERSION} is a regular GitHub Release, but remains unsigned",
                                    "This source candidate remains unsigned; publication is separate")
            return text
        with patch.object(release_contract, "_read", side_effect=candidate_copy):
            self.assertEqual(release_contract.validate_release_contract(), [])

    def test_source_identity_cannot_be_missing_stale_or_duplicated(self) -> None:
        read = release_contract._read
        for replacement in ("", SOURCE_START + "Source version: `v0.0.5`" + SOURCE_END,
                            source_version_block() * 2):
            with self.subTest(replacement=replacement):
                def changed(relative: str) -> str:
                    text = read(relative)
                    return text.replace(source_version_block(), replacement) if relative == "README.md" else text
                with patch.object(release_contract, "_read", side_effect=changed):
                    issues = release_contract.validate_release_contract()
                self.assertTrue(any("README.md:" in issue and "source" in issue for issue in issues), issues)

    def test_candidate_docs_do_not_weaken_immutable_or_asset_replacement_guards(self) -> None:
        read = release_contract._read
        for path, old, new, expected in (
            ("sdad_inspector/updater.py", 'release.get("immutable") is not True', "False", "immutable"),
            (".github/workflows/release.yml", "--draft=false", "--draft=false --clobber", "--clobber"),
            (".github/workflows/release.yml", "actions/attest@v4", "removed-attestation", "actions/attest@v4"),
        ):
            with self.subTest(path=path, expected=expected):
                def changed(relative: str) -> str:
                    text = read(relative)
                    return text.replace(old, new) if relative == path else text
                with patch.object(release_contract, "_read", side_effect=changed):
                    issues = release_contract.validate_release_contract()
                self.assertTrue(any(expected in issue for issue in issues), issues)


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
            version="0.0.4",
            architecture="X64",
        )

        archive = Path(str(evidence["archive"]))
        self.assertEqual(
            archive.name, "SDAD-Inspector-0.0.4-windows-x64.zip"
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
            version="0.0.4",
            architecture="ARM64",
        )

        archive = Path(str(evidence["archive"]))
        self.assertEqual(
            archive.name, "SDAD-Inspector-0.0.4-macos-arm64.tar.gz"
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

    def test_native_builder_uses_windows_npm_command_wrapper(self) -> None:
        requested: list[str] = []

        def fake_which(command: str) -> str:
            requested.append(command)
            return f"C:/tools/{command}"

        self.assertEqual(
            resolve_npm_executable(platform_name="nt", which=fake_which),
            "C:/tools/npm.cmd",
        )
        self.assertEqual(requested, ["npm.cmd"])

    def test_checksum_manifest_requires_one_archive_per_platform(self) -> None:
        self.output.mkdir(parents=True)
        for name in (
            "SDAD-Inspector-0.0.4-linux-x64.tar.gz",
            "SDAD-Inspector-0.0.4-macos-arm64.tar.gz",
            "SDAD-Inspector-0.0.4-windows-x64.zip",
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
