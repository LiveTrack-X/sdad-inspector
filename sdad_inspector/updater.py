from __future__ import annotations

import ctypes
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tarfile
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, Mapping, Sequence
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from . import __version__
from .errors import InspectorError
from .preferences import default_preferences_path

REPOSITORY_OWNER = "LiveTrack-X"
REPOSITORY_NAME = "sdad-inspector"
RELEASES_API = (
    f"https://api.github.com/repos/{REPOSITORY_OWNER}/{REPOSITORY_NAME}/releases"
    "?per_page=20"
)
INTERNAL_UPDATE_FLAG = "--sdad-internal-apply-update"
UPDATE_SCHEMA_VERSION = 1
MAX_API_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXECUTABLE_BYTES = 1024 * 1024 * 1024
MAX_PLAN_BYTES = 64 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
PARENT_EXIT_TIMEOUT_SECONDS = 120.0
PLAN_LIFETIME_SECONDS = 10 * 60
ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}
PUBLIC_VERSION_PATTERN = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<stage>alpha|beta|rc)\.(?P<serial>0|[1-9]\d*))?$"
)
PEP440_PRERELEASE_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:(?P<stage>a|b|rc)(?P<serial>0|[1-9]\d*))?$"
)
SHA256_PATTERN = re.compile(r"^sha256:([0-9a-f]{64})$")


class ProductUpdateError(InspectorError):
    code = "product_update_error"


@dataclass(frozen=True, order=True)
class VersionKey:
    major: int
    minor: int
    patch: int
    stage_rank: int
    serial: int


@dataclass(frozen=True)
class ReleaseCandidate:
    version: str
    tag: str
    release_url: str
    asset_name: str
    asset_url: str
    asset_size: int
    asset_sha256: str
    platform_name: str
    architecture: str


@dataclass(frozen=True)
class VerifiedUpdate:
    release: ReleaseCandidate
    executable_path: Path
    executable_sha256: str
    executable_size: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_public_version(value: str) -> VersionKey | None:
    match = PUBLIC_VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    stage = match.group("stage")
    rank = {"alpha": 0, "beta": 1, "rc": 2, None: 3}[stage]
    serial = int(match.group("serial") or 0)
    return VersionKey(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        rank,
        serial,
    )


def public_version_from_package(value: str) -> str:
    match = PEP440_PRERELEASE_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ProductUpdateError("The Inspector package version is not update-compatible.")
    base = ".".join(match.group(name) for name in ("major", "minor", "patch"))
    stage = match.group("stage")
    if stage is None:
        return base
    public_stage = {"a": "alpha", "b": "beta", "rc": "rc"}[stage]
    return f"{base}-{public_stage}.{match.group('serial')}"


CURRENT_PUBLIC_VERSION = public_version_from_package(__version__)


def normalized_platform(value: str | None = None) -> str:
    value = sys.platform if value is None else value
    if value in {"win32", "windows"}:
        return "windows"
    if value in {"darwin", "macos"}:
        return "macos"
    if value == "linux" or value.startswith("linux"):
        return "linux"
    raise ProductUpdateError(f"Automatic updates are unavailable on platform {value!r}.")


def normalized_architecture(value: str | None = None) -> str:
    value = platform.machine() if value is None else value
    normalized = value.strip().casefold().replace("_", "-")
    aliases = {
        "amd64": "x64",
        "x86-64": "x64",
        "x86_64": "x64",
        "x64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    if normalized not in aliases:
        raise ProductUpdateError(
            f"Automatic updates are unavailable on architecture {value!r}."
        )
    return aliases[normalized]


def expected_executable_name(platform_name: str) -> str:
    return "SDAD-Inspector.exe" if platform_name == "windows" else "SDAD-Inspector"


def expected_asset_name(version: str, platform_name: str, architecture: str) -> str:
    suffix = ".zip" if platform_name == "windows" else ".tar.gz"
    return f"SDAD-Inspector-{version}-{platform_name}-{architecture}{suffix}"


def default_update_root() -> Path:
    return default_preferences_path().parent / "updates"


def sha256_file(path: Path, *, maximum_bytes: int = MAX_EXECUTABLE_BYTES) -> str:
    if path.is_symlink() or not path.is_file():
        raise ProductUpdateError("An update file is missing or is not a regular file.")
    size = path.stat().st_size
    if size <= 0 or size > maximum_bytes:
        raise ProductUpdateError("An update file is empty or exceeds the bounded size.")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_stream(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    expected_bytes: int,
    maximum_bytes: int,
    progress: Callable[[int, int], None] | None = None,
) -> str:
    if expected_bytes <= 0 or expected_bytes > maximum_bytes:
        raise ProductUpdateError("The update size is outside the accepted boundary.")
    digest = hashlib.sha256()
    written = 0
    while True:
        chunk = source.read(DOWNLOAD_CHUNK_BYTES)
        if not chunk:
            break
        written += len(chunk)
        if written > expected_bytes or written > maximum_bytes:
            raise ProductUpdateError("The downloaded update exceeded its declared size.")
        destination.write(chunk)
        digest.update(chunk)
        if progress is not None:
            progress(written, expected_bytes)
    if written != expected_bytes:
        raise ProductUpdateError("The downloaded update size did not match GitHub metadata.")
    return digest.hexdigest()


def _validate_release_url(url: str, *, tag: str) -> None:
    parsed = urlsplit(url)
    expected_path = f"/{REPOSITORY_OWNER}/{REPOSITORY_NAME}/releases/tag/{tag}"
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or unquote(parsed.path) != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise ProductUpdateError("GitHub returned an unexpected release URL.")


def _validate_asset_url(url: str, *, tag: str, asset_name: str) -> None:
    parsed = urlsplit(url)
    expected_path = (
        f"/{REPOSITORY_OWNER}/{REPOSITORY_NAME}/releases/download/{tag}/{asset_name}"
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or unquote(parsed.path) != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise ProductUpdateError("GitHub returned an unexpected update asset URL.")


def _validate_download_response_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProductUpdateError("The update download redirected outside GitHub's asset hosts.")


def select_release(
    payload: object,
    *,
    current_version: str,
    platform_name: str,
    architecture: str,
) -> ReleaseCandidate | None:
    if not isinstance(payload, list):
        raise ProductUpdateError("GitHub returned an invalid releases response.")
    current_key = parse_public_version(current_version)
    if current_key is None:
        raise ProductUpdateError("The current Inspector version cannot be compared safely.")

    newer: list[tuple[VersionKey, Mapping[str, Any], str]] = []
    for item in payload:
        if not isinstance(item, Mapping) or item.get("draft") is True:
            continue
        tag = item.get("tag_name")
        if not isinstance(tag, str) or not tag.startswith("v"):
            continue
        version = tag[1:]
        key = parse_public_version(version)
        if key is not None and key > current_key:
            newer.append((key, item, version))
    if not newer:
        return None

    _, release, version = max(newer, key=lambda value: value[0])
    tag = release.get("tag_name")
    if tag != f"v{version}" or release.get("immutable") is not True:
        raise ProductUpdateError(
            "The newest release is not immutable, so it will not be installed automatically."
        )
    release_url = release.get("html_url")
    if not isinstance(release_url, str):
        raise ProductUpdateError("The immutable release is missing its canonical URL.")
    _validate_release_url(release_url, tag=tag)

    name = expected_asset_name(version, platform_name, architecture)
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ProductUpdateError("The immutable release does not contain an asset list.")
    matches = [asset for asset in assets if isinstance(asset, Mapping) and asset.get("name") == name]
    if len(matches) != 1:
        raise ProductUpdateError(f"The immutable release must contain exactly one {name} asset.")
    asset = matches[0]
    size = asset.get("size")
    digest_value = asset.get("digest")
    download_url = asset.get("browser_download_url")
    digest_match = SHA256_PATTERN.fullmatch(digest_value) if isinstance(digest_value, str) else None
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_ARCHIVE_BYTES:
        raise ProductUpdateError("The update asset has an invalid or excessive size.")
    if digest_match is None:
        raise ProductUpdateError("The update asset does not provide a valid SHA-256 digest.")
    if not isinstance(download_url, str):
        raise ProductUpdateError("The update asset is missing its download URL.")
    _validate_asset_url(download_url, tag=tag, asset_name=name)
    return ReleaseCandidate(
        version=version,
        tag=tag,
        release_url=release_url,
        asset_name=name,
        asset_url=download_url,
        asset_size=size,
        asset_sha256=digest_match.group(1),
        platform_name=platform_name,
        architecture=architecture,
    )


def extract_single_executable(
    archive_path: Path,
    destination: Path,
    *,
    platform_name: str,
) -> tuple[str, int]:
    expected_name = expected_executable_name(platform_name)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        if platform_name == "windows":
            with zipfile.ZipFile(archive_path) as archive:
                members = archive.infolist()
                if len(members) != 1:
                    raise ProductUpdateError("The update archive must contain exactly one file.")
                member = members[0]
                unix_mode = member.external_attr >> 16
                if (
                    member.filename != expected_name
                    or "/" in member.filename
                    or "\\" in member.filename
                    or member.is_dir()
                    or stat.S_ISLNK(unix_mode)
                    or not 0 < member.file_size <= MAX_EXECUTABLE_BYTES
                ):
                    raise ProductUpdateError("The update ZIP contains an unsafe executable member.")
                with archive.open(member) as source, temporary.open("xb") as target:
                    digest = _copy_stream(
                        source,
                        target,
                        expected_bytes=member.file_size,
                        maximum_bytes=MAX_EXECUTABLE_BYTES,
                    )
        else:
            with tarfile.open(archive_path, mode="r:gz") as archive:
                members = archive.getmembers()
                if len(members) != 1:
                    raise ProductUpdateError("The update archive must contain exactly one file.")
                member = members[0]
                if (
                    member.name != expected_name
                    or "/" in member.name
                    or "\\" in member.name
                    or not member.isreg()
                    or not 0 < member.size <= MAX_EXECUTABLE_BYTES
                ):
                    raise ProductUpdateError("The update TAR contains an unsafe executable member.")
                source = archive.extractfile(member)
                if source is None:
                    raise ProductUpdateError("The update executable could not be read.")
                with source, temporary.open("xb") as target:
                    digest = _copy_stream(
                        source,
                        target,
                        expected_bytes=member.size,
                        maximum_bytes=MAX_EXECUTABLE_BYTES,
                    )
        if platform_name != "windows":
            temporary.chmod(0o755)
        os.replace(temporary, destination)
        return digest, destination.stat().st_size
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        raise ProductUpdateError("The update archive could not be validated or extracted.") from exc
    finally:
        temporary.unlink(missing_ok=True)


class ProductUpdateManager:
    def __init__(
        self,
        *,
        frozen: bool | None = None,
        executable: str | Path | None = None,
        current_version: str = CURRENT_PUBLIC_VERSION,
        platform_name: str | None = None,
        architecture: str | None = None,
        update_root: str | Path | None = None,
        opener: Callable[..., Any] = urlopen,
        launcher: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self._verified: VerifiedUpdate | None = None
        self._automatic_retry_blocked = False
        self._recent_success_loaded_at: float | None = None
        self._pending_success_result: Path | None = None
        self._pending_success_backup: Path | None = None
        self._opener = opener
        self._launcher = launcher
        self.current_version = current_version
        self.executable = Path(executable or sys.executable).resolve(strict=False)
        self.update_root = Path(update_root or default_update_root()).expanduser().resolve(strict=False)
        is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        try:
            self.platform_name = normalized_platform(platform_name)
            self.architecture = normalized_architecture(architecture)
            runtime_supported = True
            unsupported_reason = None
        except ProductUpdateError as exc:
            self.platform_name = "unsupported"
            self.architecture = "unsupported"
            runtime_supported = False
            unsupported_reason = exc.message
        self.supported = bool(is_frozen and runtime_supported)
        if not is_frozen:
            unsupported_reason = "Self-update is available only in the packaged portable application."
        self._state: dict[str, Any] = {
            "supported": self.supported,
            "automatic": True,
            "current_version": self.current_version,
            "state": "idle" if self.supported else "unsupported",
            "available_version": None,
            "release_url": None,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "checked_at": None,
            "message": unsupported_reason,
            "error": None,
        }
        self._load_last_result()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def _update_state(self, **changes: Any) -> None:
        with self._lock:
            self._state.update(changes)

    def _load_last_result(self) -> None:
        try:
            results = sorted(
                self.update_root.glob("handoff-*/result.json"),
                key=lambda path: path.stat().st_mtime_ns,
                reverse=True,
            )[:1]
            if not results:
                return
            result_path = results[0]
            if result_path.is_symlink() or result_path.stat().st_size > MAX_PLAN_BYTES:
                return
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != UPDATE_SCHEMA_VERSION:
                return
            status = payload.get("status")
            version = payload.get("version")
            if status == "success" and version == self.current_version:
                cleanup_paths = self._success_cleanup_paths(result_path, payload)
                if cleanup_paths is None:
                    return
                self._pending_success_result, self._pending_success_backup = cleanup_paths
                self._recent_success_loaded_at = time.monotonic()
                self._state.update(
                    state="updated",
                    available_version=version,
                    message="The portable application was updated and relaunched successfully.",
                )
            elif status == "error" and isinstance(payload.get("message"), str):
                self._automatic_retry_blocked = True
                self._state.update(
                    state="error",
                    available_version=version if isinstance(version, str) else None,
                    error=payload["message"],
                )
        except (OSError, UnicodeError, json.JSONDecodeError):
            return

    def _success_cleanup_paths(
        self, result_path: Path, payload: Mapping[str, Any]
    ) -> tuple[Path, Path] | None:
        """Bind one success marker to this app's exact backup without trusting it."""

        try:
            root = self.update_root.resolve(strict=True)
            if result_path.is_symlink() or result_path.parent.is_symlink():
                return None
            resolved_result = result_path.resolve(strict=True)
            relative = resolved_result.relative_to(root)
            if (
                len(relative.parts) != 2
                or not relative.parts[0].startswith("handoff-")
                or relative.parts[1] != "result.json"
            ):
                return None
            backup_value = payload.get("backup_path")
            if not isinstance(backup_value, str) or not backup_value:
                return None
            expected_backup = self.executable.with_name(
                self.executable.name + ".previous"
            ).resolve(strict=False)
            declared_backup = Path(backup_value).expanduser()
            if declared_backup.is_symlink():
                return None
            if declared_backup.resolve(strict=False) != expected_backup:
                return None
            return resolved_result, expected_backup
        except (OSError, RuntimeError, ValueError):
            return None

    def acknowledge_successful_update(self) -> dict[str, Any]:
        """Consume one valid success after the replacement UI has loaded."""

        with self._lock:
            result_path = self._pending_success_result
            backup_path = self._pending_success_backup
            if self._state["state"] != "updated" or result_path is None or backup_path is None:
                return dict(self._state)
            try:
                if result_path.is_symlink() or (
                    result_path.exists() and not result_path.is_file()
                ):
                    raise ProductUpdateError(
                        "The successful update marker is unsafe and was not consumed."
                    )
                if backup_path.is_symlink():
                    raise ProductUpdateError(
                        "The previous-version backup path is unsafe and was not removed."
                    )
                if backup_path.exists():
                    if not backup_path.is_file():
                        raise ProductUpdateError(
                            "The previous-version backup path is unsafe and was not removed."
                        )
                    backup_path.unlink()
                result_path.unlink(missing_ok=True)
            except ProductUpdateError:
                raise
            except OSError as exc:
                raise ProductUpdateError(
                    "The previous update cleanup could not be completed."
                ) from exc
            self._pending_success_result = None
            self._pending_success_backup = None
            self._recent_success_loaded_at = None
            self._state.update(
                state="up_to_date",
                available_version=None,
                release_url=None,
                downloaded_bytes=0,
                total_bytes=0,
                message=None,
                error=None,
            )
            return dict(self._state)

    def start_background_check(self, *, force: bool = False) -> dict[str, Any]:
        if not self.supported:
            return self.status()
        with self._lock:
            if self._automatic_retry_blocked and not force:
                return dict(self._state)
            if (
                self._state["state"] == "updated"
                and self._recent_success_loaded_at is not None
                and time.monotonic() - self._recent_success_loaded_at < 30
                and not force
            ):
                return dict(self._state)
            if self._worker is not None and self._worker.is_alive():
                return dict(self._state)
            if self._state["state"] in {"ready", "applying"}:
                return dict(self._state)
            if force:
                self._automatic_retry_blocked = False
            self._state.update(
                state="checking",
                message=None,
                error=None,
                downloaded_bytes=0,
                total_bytes=0,
            )
            thread = threading.Thread(
                target=self._background_check,
                name="sdad-inspector-product-update",
                daemon=True,
            )
            self._worker = thread
            thread.start()
            return dict(self._state)

    def _background_check(self) -> None:
        try:
            self.check_and_download()
        except ProductUpdateError as exc:
            self._update_state(state="error", error=exc.message, message=None, checked_at=utc_now())
        except Exception:
            self._update_state(
                state="error",
                error="The update check failed unexpectedly. The current application was not changed.",
                message=None,
                checked_at=utc_now(),
            )

    def _read_releases(self) -> object:
        request = Request(
            RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"SDAD-Inspector/{self.current_version}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with self._opener(request, timeout=20) as response:
                final = urlsplit(response.geturl())
                if (
                    final.scheme != "https"
                    or final.hostname != "api.github.com"
                    or unquote(final.path)
                    != f"/repos/{REPOSITORY_OWNER}/{REPOSITORY_NAME}/releases"
                ):
                    raise ProductUpdateError("The update API redirected unexpectedly.")
                body = response.read(MAX_API_BYTES + 1)
        except ProductUpdateError:
            raise
        except OSError as exc:
            raise ProductUpdateError("The GitHub update service could not be reached.") from exc
        if len(body) > MAX_API_BYTES:
            raise ProductUpdateError("The GitHub releases response exceeded the bounded size.")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProductUpdateError("GitHub returned an invalid releases response.") from exc

    def check_and_download(self) -> dict[str, Any]:
        if not self.supported:
            return self.status()
        release = select_release(
            self._read_releases(),
            current_version=self.current_version,
            platform_name=self.platform_name,
            architecture=self.architecture,
        )
        if release is None:
            self._verified = None
            self._update_state(
                state="up_to_date",
                checked_at=utc_now(),
                available_version=None,
                release_url=None,
                message="This portable application is up to date.",
                error=None,
            )
            return self.status()
        self._update_state(
            state="downloading",
            available_version=release.version,
            release_url=release.release_url,
            downloaded_bytes=0,
            total_bytes=release.asset_size,
            message="A newer immutable release is downloading in the background.",
            error=None,
        )
        verified = self._download_release(release)
        with self._lock:
            self._verified = verified
            self._state.update(
                state="ready",
                checked_at=utc_now(),
                downloaded_bytes=release.asset_size,
                total_bytes=release.asset_size,
                message="The verified update is ready and will restart automatically.",
                error=None,
            )
        return self.status()

    def _download_release(self, release: ReleaseCandidate) -> VerifiedUpdate:
        version_root = self.update_root / (
            f"download-{release.version}-{release.platform_name}-{release.architecture}"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        archive_path = version_root / release.asset_name
        archive_tmp = archive_path.with_name(archive_path.name + ".tmp")
        executable_path = version_root / expected_executable_name(release.platform_name)
        archive_tmp.unlink(missing_ok=True)
        executable_path.unlink(missing_ok=True)
        request = Request(
            release.asset_url,
            headers={
                "Accept": "application/octet-stream",
                "User-Agent": f"SDAD-Inspector/{self.current_version}",
            },
        )
        try:
            with self._opener(request, timeout=60) as response:
                _validate_download_response_url(response.geturl())
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        if int(content_length) != release.asset_size:
                            raise ProductUpdateError(
                                "The downloaded update length disagreed with GitHub metadata."
                            )
                    except ValueError as exc:
                        raise ProductUpdateError("The update response had an invalid length.") from exc
                with archive_tmp.open("xb") as target:
                    digest = _copy_stream(
                        response,
                        target,
                        expected_bytes=release.asset_size,
                        maximum_bytes=MAX_ARCHIVE_BYTES,
                        progress=lambda current, total: self._update_state(
                            downloaded_bytes=current, total_bytes=total
                        ),
                    )
        except ProductUpdateError:
            raise
        except OSError as exc:
            raise ProductUpdateError("The update asset could not be downloaded safely.") from exc
        finally:
            if archive_tmp.exists() and archive_tmp.stat().st_size != release.asset_size:
                archive_tmp.unlink(missing_ok=True)
        if not hmac.compare_digest(digest, release.asset_sha256):
            archive_tmp.unlink(missing_ok=True)
            raise ProductUpdateError("The update asset SHA-256 digest did not match GitHub metadata.")
        os.replace(archive_tmp, archive_path)
        executable_sha256, executable_size = extract_single_executable(
            archive_path,
            executable_path,
            platform_name=release.platform_name,
        )
        return VerifiedUpdate(
            release=release,
            executable_path=executable_path,
            executable_sha256=executable_sha256,
            executable_size=executable_size,
        )

    def launch_apply(self, *, project_root: str | Path) -> dict[str, Any]:
        if not self.supported:
            raise ProductUpdateError("Self-update is unavailable outside the packaged application.")
        with self._lock:
            verified = self._verified
            if self._state["state"] != "ready" or verified is None:
                raise ProductUpdateError("No verified product update is ready to apply.")
        target = self.executable.resolve(strict=True)
        if target.is_symlink() or target.name != expected_executable_name(self.platform_name):
            raise ProductUpdateError("The running portable executable path is not update-compatible.")
        project = Path(project_root).expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ProductUpdateError("The active project path is unavailable for relaunch.")
        handoff = self.update_root / (
            f"handoff-{verified.release.version}-{secrets.token_hex(8)}"
        )
        handoff.mkdir(parents=True, exist_ok=False)
        candidate = handoff / target.name
        helper_name = "SDAD-Inspector-update-helper.exe" if self.platform_name == "windows" else "SDAD-Inspector-update-helper"
        helper = handoff / helper_name
        shutil.copy2(verified.executable_path, candidate)
        shutil.copy2(verified.executable_path, helper)
        if self.platform_name != "windows":
            candidate.chmod(0o755)
            helper.chmod(0o755)
        if not hmac.compare_digest(sha256_file(candidate), verified.executable_sha256):
            raise ProductUpdateError("The staged update changed before handoff.")
        if not hmac.compare_digest(sha256_file(helper), verified.executable_sha256):
            raise ProductUpdateError("The copied update helper changed before launch.")
        plan = {
            "schema_version": UPDATE_SCHEMA_VERSION,
            "created_at": utc_now(),
            "expires_at_epoch": time.time() + PLAN_LIFETIME_SECONDS,
            "parent_pid": (
                os.getppid()
                if bool(getattr(sys, "frozen", False)) and os.getppid() > 0
                else os.getpid()
            ),
            "target_path": str(target),
            "target_sha256": sha256_file(target),
            "candidate_path": str(candidate),
            "candidate_sha256": verified.executable_sha256,
            "candidate_bytes": verified.executable_size,
            "project_root": str(project),
            "version": verified.release.version,
            "platform": self.platform_name,
            "architecture": self.architecture,
            "result_path": str(handoff / "result.json"),
        }
        plan_path = handoff / "apply-plan.json"
        encoded = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(encoded) > MAX_PLAN_BYTES:
            raise ProductUpdateError("The bounded update handoff plan is too large.")
        plan_path.write_bytes(encoded)
        try:
            plan_path.chmod(0o600)
        except OSError:
            pass
        command = [str(helper), INTERNAL_UPDATE_FLAG, str(plan_path)]
        kwargs: dict[str, Any] = {
            "cwd": str(handoff),
            "close_fds": True,
        }
        if self.platform_name == "windows":
            kwargs["creationflags"] = (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        else:
            kwargs["start_new_session"] = True
        try:
            self._launcher(command, **kwargs)
        except OSError as exc:
            raise ProductUpdateError("The verified update helper could not be started.") from exc
        self._update_state(
            state="applying",
            message="The verified helper is waiting to replace and relaunch this application.",
            error=None,
        )
        return self.status()


def _bounded_plan(plan_path: str | Path, *, update_root: Path) -> tuple[Path, dict[str, Any]]:
    root = update_root.expanduser().resolve(strict=True)
    raw = Path(plan_path).expanduser()
    if raw.is_symlink():
        raise ProductUpdateError("The update handoff plan may not be a symbolic link.")
    path = raw.resolve(strict=True)
    try:
        path.parent.relative_to(root)
    except ValueError as exc:
        raise ProductUpdateError("The update handoff plan is outside the per-user update root.") from exc
    if path.name != "apply-plan.json" or path.stat().st_size > MAX_PLAN_BYTES:
        raise ProductUpdateError("The update handoff plan is invalid or too large.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProductUpdateError("The update handoff plan could not be read.") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != UPDATE_SCHEMA_VERSION:
        raise ProductUpdateError("The update handoff plan schema is unsupported.")
    return path, payload


def _plan_path(payload: Mapping[str, Any], key: str, *, parent: Path) -> Path:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ProductUpdateError(f"The update handoff is missing {key}.")
    raw = Path(value)
    if raw.is_symlink():
        raise ProductUpdateError(f"The update handoff {key} may not be a symbolic link.")
    resolved = raw.resolve(strict=True)
    if key in {"candidate_path", "result_path"}:
        try:
            resolved.relative_to(parent)
        except ValueError as exc:
            raise ProductUpdateError(f"The update handoff {key} left its staging directory.") from exc
    return resolved


def wait_for_process_exit(parent_pid: int, timeout: float = PARENT_EXIT_TIMEOUT_SECONDS) -> None:
    if parent_pid <= 0 or parent_pid == os.getpid():
        raise ProductUpdateError("The update helper received an invalid parent process.")
    if sys.platform == "win32":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(0x00100000, 0, parent_pid)
        if not handle:
            error = ctypes.get_last_error()
            if error in {87, 1168}:
                return
            raise ProductUpdateError("The update helper could not observe the parent process.")
        try:
            result = kernel32.WaitForSingleObject(handle, int(timeout * 1000))
            if result == 0:
                return
            if result == 0x102:
                raise ProductUpdateError("The running application did not exit before update timeout.")
            raise ProductUpdateError("The update helper could not wait for the parent process.")
        finally:
            kernel32.CloseHandle(handle)
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.kill(parent_pid, 0)
        except ProcessLookupError:
            return
        except PermissionError as exc:
            raise ProductUpdateError("The update helper cannot observe the parent process.") from exc
        if time.monotonic() >= deadline:
            raise ProductUpdateError("The running application did not exit before update timeout.")
        time.sleep(0.1)


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(encoded) > MAX_PLAN_BYTES:
        return
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
    except OSError:
        pass
    finally:
        temporary.unlink(missing_ok=True)


def _launch_application(
    target: Path,
    project_root: Path,
    *,
    launcher: Callable[..., Any],
) -> None:
    kwargs: dict[str, Any] = {"cwd": str(target.parent), "close_fds": True}
    if sys.platform != "win32":
        kwargs["start_new_session"] = True
    launcher([str(target), str(project_root)], **kwargs)


SHCNE_UPDATEITEM = 0x00002000
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_IDLIST = 0x0000
SHCNF_PATHW = 0x0005
SHCNF_FLUSH = 0x1000


def refresh_windows_icon_cache(executable_path: str | Path) -> bool:
    """Refresh one executable path and then Explorer's icon associations."""

    if sys.platform != "win32":
        return False
    try:
        resolved_path = str(Path(executable_path).resolve(strict=False))
        shell32 = ctypes.OleDLL("shell32")
        shell32.SHChangeNotify.argtypes = [
            ctypes.c_long,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        shell32.SHChangeNotify.restype = None
        path_pointer = ctypes.c_wchar_p(resolved_path)
        shell32.SHChangeNotify(
            SHCNE_UPDATEITEM,
            SHCNF_PATHW | SHCNF_FLUSH,
            ctypes.cast(path_pointer, ctypes.c_void_p),
            None,
        )
        shell32.SHChangeNotify(
            SHCNE_ASSOCCHANGED,
            SHCNF_IDLIST | SHCNF_FLUSH,
            None,
            None,
        )
        return True
    except (AttributeError, OSError, RuntimeError, ValueError):
        return False


def apply_update_plan(
    plan_path: str | Path,
    *,
    update_root: str | Path | None = None,
    wait_for_exit: Callable[[int, float], None] = wait_for_process_exit,
    launcher: Callable[..., Any] = subprocess.Popen,
    icon_cache_refresher: Callable[[Path], bool] = refresh_windows_icon_cache,
) -> int:
    root = Path(update_root or default_update_root())
    result_path: Path | None = None
    target: Path | None = None
    backup: Path | None = None
    project_root: Path | None = None
    version: str | None = None
    replaced = False
    try:
        plan_file, payload = _bounded_plan(plan_path, update_root=root)
        parent = plan_file.parent
        expires = payload.get("expires_at_epoch")
        parent_pid = payload.get("parent_pid")
        candidate_bytes = payload.get("candidate_bytes")
        version = payload.get("version")
        platform_name = payload.get("platform")
        if (
            not isinstance(expires, (int, float))
            or expires < time.time()
            or expires > time.time() + PLAN_LIFETIME_SECONDS + 30
            or not isinstance(parent_pid, int)
            or isinstance(parent_pid, bool)
            or not isinstance(candidate_bytes, int)
            or isinstance(candidate_bytes, bool)
            or not 0 < candidate_bytes <= MAX_EXECUTABLE_BYTES
            or not isinstance(version, str)
            or parse_public_version(version) is None
            or platform_name != normalized_platform()
        ):
            raise ProductUpdateError("The update handoff plan contains invalid identity fields.")
        candidate = _plan_path(payload, "candidate_path", parent=parent)
        target_value = payload.get("target_path")
        project_value = payload.get("project_root")
        result_value = payload.get("result_path")
        if not all(isinstance(value, str) and value for value in (target_value, project_value, result_value)):
            raise ProductUpdateError("The update handoff plan is missing required paths.")
        target_raw = Path(target_value)
        if target_raw.is_symlink():
            raise ProductUpdateError("The update target may not be a symbolic link.")
        target = target_raw.resolve(strict=True)
        project_root = Path(project_value).resolve(strict=True)
        result_path = Path(result_value).resolve(strict=False)
        try:
            result_path.relative_to(parent)
        except ValueError as exc:
            raise ProductUpdateError("The update result path left its staging directory.") from exc
        if (
            target.name != expected_executable_name(platform_name)
            or not target.is_file()
            or not project_root.is_dir()
            or candidate.name != target.name
            or candidate.stat().st_size != candidate_bytes
        ):
            raise ProductUpdateError("The update handoff paths do not match the portable contract.")
        expected_candidate = payload.get("candidate_sha256")
        expected_target = payload.get("target_sha256")
        if not (
            isinstance(expected_candidate, str)
            and re.fullmatch(r"[0-9a-f]{64}", expected_candidate)
            and isinstance(expected_target, str)
            and re.fullmatch(r"[0-9a-f]{64}", expected_target)
        ):
            raise ProductUpdateError("The update handoff digests are invalid.")
        if not hmac.compare_digest(sha256_file(candidate), expected_candidate):
            raise ProductUpdateError("The staged update changed before replacement.")
        if not hmac.compare_digest(sha256_file(target), expected_target):
            raise ProductUpdateError("The running executable changed before replacement.")

        wait_for_exit(parent_pid, PARENT_EXIT_TIMEOUT_SECONDS)
        if not hmac.compare_digest(sha256_file(candidate), expected_candidate):
            raise ProductUpdateError("The staged update changed while waiting for shutdown.")
        if not hmac.compare_digest(sha256_file(target), expected_target):
            raise ProductUpdateError("The update target changed while waiting for shutdown.")

        backup = target.with_name(target.name + ".previous")
        if backup.exists() or backup.is_symlink():
            if backup.is_symlink() or not backup.is_file():
                raise ProductUpdateError("The previous-version backup path is unsafe.")
            backup.unlink()
        replacement = target.with_name(f".{target.name}.update-{secrets.token_hex(6)}")
        shutil.copy2(candidate, replacement)
        if platform_name != "windows":
            replacement.chmod(0o755)
        if not hmac.compare_digest(sha256_file(replacement), expected_candidate):
            replacement.unlink(missing_ok=True)
            raise ProductUpdateError("The replacement copy failed its final digest check.")
        os.replace(target, backup)
        try:
            os.replace(replacement, target)
            replaced = True
        except Exception:
            os.replace(backup, target)
            raise
        _write_result(
            result_path,
            {
                "schema_version": UPDATE_SCHEMA_VERSION,
                "status": "success",
                "version": version,
                "updated_at": utc_now(),
                "backup_path": str(backup),
            },
        )
        if platform_name == "windows":
            icon_cache_refresher(target)
        _launch_application(target, project_root, launcher=launcher)
        return 0
    except Exception as exc:
        message = exc.message if isinstance(exc, ProductUpdateError) else (
            "The update could not replace the portable executable. The previous version was retained."
        )
        if replaced and target is not None and backup is not None and backup.is_file():
            try:
                target.unlink(missing_ok=True)
                os.replace(backup, target)
                replaced = False
            except OSError:
                message = "The update failed and automatic rollback could not be completed."
        if result_path is not None:
            _write_result(
                result_path,
                {
                    "schema_version": UPDATE_SCHEMA_VERSION,
                    "status": "error",
                    "version": version,
                    "updated_at": utc_now(),
                    "message": message,
                },
            )
        if target is not None and project_root is not None and target.is_file():
            try:
                _launch_application(target, project_root, launcher=launcher)
            except OSError:
                pass
        return 2
