from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from sdad_inspector.updater import (
    INTERNAL_UPDATE_FLAG,
    UPDATE_SCHEMA_VERSION,
    ProductUpdateError,
    ProductUpdateManager,
    ReleaseCandidate,
    VerifiedUpdate,
    apply_update_plan,
    expected_asset_name,
    expected_executable_name,
    extract_single_executable,
    normalized_platform,
    parse_public_version,
    public_version_from_package,
    select_release,
    sha256_file,
)


def release_payload(
    version: str,
    *,
    platform_name: str = "windows",
    architecture: str = "x64",
    immutable: bool = True,
    digest: str = "a" * 64,
    size: int = 128,
) -> dict[str, object]:
    tag = f"v{version}"
    name = expected_asset_name(version, platform_name, architecture)
    return {
        "tag_name": tag,
        "draft": False,
        "prerelease": "-" in version,
        "immutable": immutable,
        "html_url": f"https://github.com/LiveTrack-X/sdad-inspector/releases/tag/{tag}",
        "assets": [
            {
                "name": name,
                "size": size,
                "digest": f"sha256:{digest}",
                "browser_download_url": (
                    "https://github.com/LiveTrack-X/sdad-inspector/releases/download/"
                    f"{tag}/{name}"
                ),
            }
        ],
    }


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, url: str, *, content_length: int | None = None) -> None:
        super().__init__(payload)
        self._url = url
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def zip_payload(name: str, content: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return output.getvalue()


class VersionAndReleaseTests(unittest.TestCase):
    def test_versions_compare_prereleases_before_stable(self) -> None:
        self.assertLess(parse_public_version("v0.0.1-alpha.3"), parse_public_version("0.0.1-beta.1"))
        self.assertLess(parse_public_version("0.0.1-rc.2"), parse_public_version("0.0.1"))
        self.assertEqual(public_version_from_package("0.0.1a3"), "0.0.1-alpha.3")

    def test_selects_exact_newer_immutable_platform_asset(self) -> None:
        selected = select_release(
            [release_payload("0.0.2-alpha.1"), release_payload("0.0.1-alpha.3")],
            current_version="0.0.1-alpha.3",
            platform_name="windows",
            architecture="x64",
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.version, "0.0.2-alpha.1")  # type: ignore[union-attr]
        self.assertEqual(selected.asset_sha256, "a" * 64)  # type: ignore[union-attr]

    def test_rejects_newest_mutable_release_instead_of_installing_older(self) -> None:
        with self.assertRaisesRegex(ProductUpdateError, "not immutable"):
            select_release(
                [
                    release_payload("0.0.2-alpha.2", immutable=False),
                    release_payload("0.0.2-alpha.1", immutable=True),
                ],
                current_version="0.0.1-alpha.3",
                platform_name="windows",
                architecture="x64",
            )

    def test_rejects_missing_digest_and_wrong_asset_url(self) -> None:
        missing = release_payload("0.0.2-alpha.1", digest="not-a-digest")
        with self.assertRaisesRegex(ProductUpdateError, "SHA-256"):
            select_release(
                [missing],
                current_version="0.0.1-alpha.3",
                platform_name="windows",
                architecture="x64",
            )
        wrong = release_payload("0.0.2-alpha.1")
        wrong["assets"][0]["browser_download_url"] = "https://example.com/update.zip"  # type: ignore[index]
        with self.assertRaisesRegex(ProductUpdateError, "unexpected update asset URL"):
            select_release(
                [wrong],
                current_version="0.0.1-alpha.3",
                platform_name="windows",
                architecture="x64",
            )


class ArchiveTests(unittest.TestCase):
    def test_extracts_exact_single_windows_executable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "update.zip"
            content = b"portable-update"
            archive.write_bytes(zip_payload("SDAD-Inspector.exe", content))
            destination = root / "SDAD-Inspector.exe"
            digest, size = extract_single_executable(archive, destination, platform_name="windows")
            self.assertEqual(destination.read_bytes(), content)
            self.assertEqual(digest, hashlib.sha256(content).hexdigest())
            self.assertEqual(size, len(content))

    def test_rejects_traversal_and_multiple_zip_members(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            traversal = root / "traversal.zip"
            traversal.write_bytes(zip_payload("../SDAD-Inspector.exe", b"bad"))
            with self.assertRaises(ProductUpdateError):
                extract_single_executable(traversal, root / "out.exe", platform_name="windows")
            multiple = root / "multiple.zip"
            with zipfile.ZipFile(multiple, "w") as archive:
                archive.writestr("SDAD-Inspector.exe", b"one")
                archive.writestr("extra.txt", b"two")
            with self.assertRaisesRegex(ProductUpdateError, "exactly one"):
                extract_single_executable(multiple, root / "other.exe", platform_name="windows")

    def test_rejects_tar_symlink_member(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive = root / "update.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                member = tarfile.TarInfo("SDAD-Inspector")
                member.type = tarfile.SYMTYPE
                member.linkname = "elsewhere"
                output.addfile(member)
            with self.assertRaises(ProductUpdateError):
                extract_single_executable(archive, root / "SDAD-Inspector", platform_name="linux")


class ManagerTests(unittest.TestCase):
    def test_failed_replacement_blocks_automatic_retry_loop(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = root / "updates" / "handoff-failed" / "result.json"
            result.parent.mkdir(parents=True)
            result.write_text(
                json.dumps(
                    {
                        "schema_version": UPDATE_SCHEMA_VERSION,
                        "status": "error",
                        "version": "0.0.2-alpha.1",
                        "message": "replacement denied",
                    }
                ),
                encoding="utf-8",
            )
            calls: list[object] = []

            def opener(*args: object, **kwargs: object) -> object:
                calls.append((args, kwargs))
                raise AssertionError("automatic retry must stay blocked")

            manager = ProductUpdateManager(
                frozen=True,
                executable=root / "SDAD-Inspector.exe",
                platform_name="windows",
                architecture="x64",
                update_root=root / "updates",
                opener=opener,
            )
            self.assertEqual(manager.status()["state"], "error")
            self.assertEqual(manager.start_background_check()["state"], "error")
            self.assertEqual(calls, [])

    def test_source_mode_never_contacts_network_or_applies(self) -> None:
        calls: list[object] = []

        def opener(*args: object, **kwargs: object) -> object:
            calls.append((args, kwargs))
            raise AssertionError("network should not be used")

        manager = ProductUpdateManager(frozen=False, opener=opener)
        self.assertEqual(manager.start_background_check()["state"], "unsupported")
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(ProductUpdateError, "unavailable"):
            manager.launch_apply(project_root=Path.cwd())

    def test_download_requires_github_digest_match(self) -> None:
        archive = zip_payload("SDAD-Inspector.exe", b"new executable")
        release = release_payload(
            "0.0.2-alpha.1",
            digest="0" * 64,
            size=len(archive),
        )
        responses = [
            FakeResponse(
                json.dumps([release]).encode(),
                "https://api.github.com/repos/LiveTrack-X/sdad-inspector/releases?per_page=20",
            ),
            FakeResponse(
                archive,
                "https://release-assets.githubusercontent.com/github-production-release-asset/update",
                content_length=len(archive),
            ),
        ]

        def opener(*_args: object, **_kwargs: object) -> FakeResponse:
            return responses.pop(0)

        with tempfile.TemporaryDirectory() as raw:
            manager = ProductUpdateManager(
                frozen=True,
                executable=Path(raw) / "SDAD-Inspector.exe",
                platform_name="windows",
                architecture="x64",
                update_root=Path(raw) / "updates",
                opener=opener,
            )
            with self.assertRaisesRegex(ProductUpdateError, "SHA-256"):
                manager.check_and_download()

    def test_ready_update_launches_copied_helper_with_bounded_plan(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            platform_name = normalized_platform()
            executable_name = expected_executable_name(platform_name)
            target = root / executable_name
            staged = root / "staged" / executable_name
            project = root / "project"
            staged.parent.mkdir()
            project.mkdir()
            target.write_bytes(b"old executable")
            staged.write_bytes(b"new executable")
            if platform_name != "windows":
                target.chmod(0o755)
                staged.chmod(0o755)
            launches: list[tuple[list[str], dict[str, object]]] = []

            def launcher(command: list[str], **kwargs: object) -> object:
                launches.append((command, kwargs))
                return object()

            manager = ProductUpdateManager(
                frozen=True,
                executable=target,
                platform_name=platform_name,
                architecture="x64",
                update_root=root / "updates",
                launcher=launcher,
            )
            release = ReleaseCandidate(
                version="0.0.2-alpha.1",
                tag="v0.0.2-alpha.1",
                release_url="https://github.com/LiveTrack-X/sdad-inspector/releases/tag/v0.0.2-alpha.1",
                asset_name="fixture",
                asset_url="https://github.com/LiveTrack-X/sdad-inspector/releases/download/v0.0.2-alpha.1/fixture",
                asset_size=1,
                asset_sha256="0" * 64,
                platform_name=platform_name,
                architecture="x64",
            )
            manager._verified = VerifiedUpdate(  # noqa: SLF001 - focused handoff contract
                release=release,
                executable_path=staged,
                executable_sha256=sha256_file(staged),
                executable_size=staged.stat().st_size,
            )
            manager._update_state(state="ready", available_version=release.version)  # noqa: SLF001
            status = manager.launch_apply(project_root=project)
            self.assertEqual(status["state"], "applying")
            self.assertEqual(len(launches), 1)
            command, _ = launches[0]
            self.assertEqual(command[1], INTERNAL_UPDATE_FLAG)
            plan = json.loads(Path(command[2]).read_text(encoding="utf-8"))
            self.assertEqual(plan["target_path"], str(target.resolve()))
            self.assertEqual(plan["candidate_sha256"], sha256_file(staged))


class ApplyPlanTests(unittest.TestCase):
    def _plan(self, root: Path, *, old: bytes = b"old", new: bytes = b"new") -> tuple[Path, Path, Path, Path]:
        platform_name = normalized_platform()
        name = expected_executable_name(platform_name)
        update_root = root / "updates"
        handoff = update_root / "handoff-test"
        target = root / "portable" / name
        candidate = handoff / name
        project = root / "project"
        target.parent.mkdir()
        handoff.mkdir(parents=True)
        project.mkdir()
        target.write_bytes(old)
        candidate.write_bytes(new)
        if platform_name != "windows":
            target.chmod(0o755)
            candidate.chmod(0o755)
        plan = {
            "schema_version": UPDATE_SCHEMA_VERSION,
            "created_at": "2026-07-15T00:00:00Z",
            "expires_at_epoch": time.time() + 300,
            "parent_pid": 424242,
            "target_path": str(target.resolve()),
            "target_sha256": sha256_file(target),
            "candidate_path": str(candidate.resolve()),
            "candidate_sha256": sha256_file(candidate),
            "candidate_bytes": candidate.stat().st_size,
            "project_root": str(project.resolve()),
            "version": "0.0.2-alpha.1",
            "platform": platform_name,
            "architecture": "x64",
            "result_path": str((handoff / "result.json").resolve()),
        }
        plan_path = handoff / "apply-plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        return update_root, plan_path, target, project

    def test_replaces_target_keeps_backup_and_relaunches_original_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            update_root, plan_path, target, project = self._plan(root)
            launches: list[list[str]] = []

            def launcher(command: list[str], **_kwargs: object) -> object:
                launches.append(command)
                return object()

            result = apply_update_plan(
                plan_path,
                update_root=update_root,
                wait_for_exit=lambda _pid, _timeout: None,
                launcher=launcher,
            )
            self.assertEqual(result, 0)
            self.assertEqual(target.read_bytes(), b"new")
            self.assertEqual(target.with_name(target.name + ".previous").read_bytes(), b"old")
            self.assertEqual(launches, [[str(target), str(project)]])
            payload = json.loads((plan_path.parent / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "success")

    def test_launch_failure_rolls_back_and_records_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            update_root, plan_path, target, _project = self._plan(root)

            def launcher(*_args: object, **_kwargs: object) -> object:
                raise OSError("cannot launch")

            result = apply_update_plan(
                plan_path,
                update_root=update_root,
                wait_for_exit=lambda _pid, _timeout: None,
                launcher=launcher,
            )
            self.assertEqual(result, 2)
            self.assertEqual(target.read_bytes(), b"old")
            payload = json.loads((plan_path.parent / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "error")

    def test_plan_outside_update_root_is_refused_without_target_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            update_root, plan_path, target, _project = self._plan(root)
            outside = root / "outside.json"
            outside.write_bytes(plan_path.read_bytes())
            result = apply_update_plan(
                outside,
                update_root=update_root,
                wait_for_exit=lambda _pid, _timeout: None,
                launcher=lambda *_args, **_kwargs: object(),
            )
            self.assertEqual(result, 2)
            self.assertEqual(target.read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
