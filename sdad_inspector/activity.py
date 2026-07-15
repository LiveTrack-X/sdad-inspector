from __future__ import annotations

import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import BoundedReadError, InspectorError, PathSafetyError
from .paths import read_bounded_text, safe_project_path
from .state import load_control_state

MAX_GIT_OUTPUT_BYTES = 256 * 1024
MAX_STATUS_ENTRIES = 160
MAX_COMMITS = 20
MAX_HANDOFFS = 16
GIT_TIMEOUT_SECONDS = 3.0


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _iso_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z")


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _run_git(root: Path, arguments: list[str], *, output_limit: int) -> bytes:
    command = [
        "git",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-C",
        str(root),
        *arguments,
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            env=_git_environment(),
            creationflags=creationflags,
        )
    except FileNotFoundError as exc:
        raise InspectorError("Git is unavailable on this system.", details={"code": "git_unavailable"}) from exc
    except subprocess.TimeoutExpired as exc:
        raise InspectorError("The read-only Git probe timed out.", details={"code": "git_timeout"}) from exc
    if len(completed.stdout) > output_limit or len(completed.stderr) > 16 * 1024:
        raise InspectorError("The read-only Git probe exceeded its output budget.", details={"code": "git_output_limit"})
    if completed.returncode != 0:
        raise InspectorError(
            "The selected project is not available through Git.",
            details={"code": "not_git_repository", "exit_code": completed.returncode},
        )
    return completed.stdout


def _safe_observed_path(root: Path, relative: str) -> tuple[str, str | None] | None:
    normalized = relative.replace("\\", "/")
    try:
        candidate = safe_project_path(
            root,
            normalized,
            purpose="Git observed path",
            must_exist=False,
            regular_file=False,
        )
    except PathSafetyError:
        return None
    modified_at: str | None = None
    try:
        if candidate.exists() and not candidate.is_symlink():
            modified_at = _iso_from_timestamp(candidate.stat().st_mtime)
    except OSError:
        pass
    return normalized, modified_at


def _kind(status: str) -> str:
    if status == "??":
        return "untracked"
    if "R" in status:
        return "renamed"
    if "C" in status:
        return "copied"
    if "D" in status:
        return "deleted"
    if "A" in status:
        return "added"
    if "U" in status:
        return "conflicted"
    return "modified"


def parse_porcelain(root: Path, output: bytes) -> tuple[list[dict[str, Any]], bool]:
    tokens = output.split(b"\x00")
    entries: list[dict[str, Any]] = []
    index = 0
    truncated = False
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4 or token[2:3] != b" ":
            continue
        status = token[:2].decode("ascii", "replace")
        path = token[3:].decode("utf-8", "replace")
        previous_path: str | None = None
        if any(code in status for code in ("R", "C")) and index < len(tokens):
            previous_path = tokens[index].decode("utf-8", "replace")
            index += 1
        safe = _safe_observed_path(root, path)
        if safe is None:
            continue
        normalized, modified_at = safe
        safe_previous = _safe_observed_path(root, previous_path) if previous_path else None
        entries.append(
            {
                "path": normalized,
                "previous_path": safe_previous[0] if safe_previous else None,
                "status": status,
                "kind": _kind(status),
                "modified_at": modified_at,
            }
        )
        if len(entries) >= MAX_STATUS_ENTRIES:
            truncated = any(tokens[index:])
            break
    entries.sort(key=lambda item: item.get("modified_at") or "", reverse=True)
    return entries, truncated


def parse_commits(output: bytes) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for raw in output.split(b"\x1e"):
        raw = raw.strip(b"\r\n")
        if not raw:
            continue
        fields = raw.split(b"\x1f", 3)
        if len(fields) != 4:
            continue
        revision, short_revision, committed_at, subject = (
            field.decode("utf-8", "replace").strip() for field in fields
        )
        commits.append(
            {
                "revision": revision,
                "short_revision": short_revision,
                "committed_at": committed_at,
                "subject": subject[:300],
            }
        )
        if len(commits) >= MAX_COMMITS:
            break
    return commits


def _handoff_candidates(root: Path, state: dict[str, Any]) -> tuple[list[str], str | None]:
    current = state.get("current_handoff") or {}
    current_path = current.get("path") if current.get("declared") else None
    candidates: list[str] = []
    if isinstance(current_path, str):
        candidates.append(current_path)
    for routed in state.get("routed_docs") or []:
        if isinstance(routed, str) and "handoff" in routed.casefold() and routed.casefold().endswith(".md"):
            candidates.append(routed)
    for relative_dir in ("docs/sdad/handoffs", "docs/handoffs"):
        try:
            directory = safe_project_path(
                root,
                relative_dir,
                purpose="handoff history directory",
                must_exist=False,
                regular_file=False,
            )
            if not directory.is_dir() or directory.is_symlink():
                continue
            observed = 0
            for child in directory.iterdir():
                observed += 1
                if observed > 200:
                    break
                if child.suffix.casefold() == ".md":
                    candidates.append(f"{relative_dir}/{child.name}")
        except (OSError, PathSafetyError):
            continue
    return list(dict.fromkeys(candidates)), current_path if isinstance(current_path, str) else None


def _handoff_history(root: Path) -> list[dict[str, Any]]:
    try:
        state, _ = load_control_state(root)
    except InspectorError:
        return []
    candidates, current_path = _handoff_candidates(root, state)
    records: list[dict[str, Any]] = []
    for relative in candidates[:64]:
        try:
            path = safe_project_path(root, relative, purpose="handoff history", must_exist=True)
            text = read_bounded_text(
                root,
                relative,
                purpose="handoff history",
                required=True,
                max_bytes=32 * 1024,
                max_lines=250,
            )
            assert text is not None
        except (InspectorError, OSError):
            continue
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
        summary = next(
            (
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.startswith("#") and not line.startswith("Status:")
            ),
            "",
        )
        records.append(
            {
                "path": relative.replace("\\", "/"),
                "title": title[:200],
                "summary": summary[:300],
                "modified_at": _iso_from_timestamp(path.stat().st_mtime),
                "current": relative == current_path,
            }
        )
    records.sort(key=lambda item: item["modified_at"], reverse=True)
    return records[:MAX_HANDOFFS]


def load_development_activity(root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    scanned_at = _now()
    try:
        status_output = _run_git(
            root,
            ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
            output_limit=MAX_GIT_OUTPUT_BYTES,
        )
        files, truncated = parse_porcelain(root, status_output)
        try:
            commit_output = _run_git(
                root,
                ["log", f"-n{MAX_COMMITS}", "--date=iso-strict", "--format=%x1e%H%x1f%h%x1f%cI%x1f%s"],
                output_limit=64 * 1024,
            )
            commits = parse_commits(commit_output)
        except InspectorError:
            # A valid repository without a first commit still has useful status data.
            commits = []
        error: dict[str, Any] | None = None
        available = True
    except InspectorError as exc:
        files = []
        commits = []
        truncated = False
        available = False
        error = {"code": str(exc.details.get("code") or exc.code), "message": exc.message}
    counts: dict[str, int] = {}
    for item in files:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return {
        "project_root": str(root),
        "available": available,
        "worktree_status": "changed" if files else ("clean" if available else "unavailable"),
        "scanned_at": scanned_at,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "changed_count": len(files),
        "truncated": truncated,
        "counts": counts,
        "files": files,
        "commits": commits,
        "handoffs": _handoff_history(root),
        "error": error,
    }
