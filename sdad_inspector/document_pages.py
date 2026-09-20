"""Explicit bounded pages from the selected, authenticated SDAD context helper."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .engine import EngineInfo, _run, probe_engine
from .errors import InspectorError, UnsupportedContractError
from .paths import safe_project_path
from .protocols import DEFAULT_PROTOCOL_ADAPTER_ID, ProtocolAdapter

MAX_PAGE_LINES = 500
MAX_PAGE_BYTES = 50_000
MAX_FILE_BYTES = 1_000_000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
# -I excludes project/environment imports. Only this authenticated script's
# directory is added; sdad_context.py itself does not bootstrap that directory.
_CONTEXT_BOOTSTRAP = "import pathlib,runpy,sys;script=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,str(pathlib.Path(script).parent));runpy.run_path(script,run_name='__main__')"


class DocumentPageError(InspectorError):
    def __init__(self, message: str, code: str = "document_page_unavailable"):
        super().__init__(message)
        self.code = code


def _relative(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise DocumentPageError("Select one declared document.", "document_page_invalid")
    value = value.replace("\\", "/")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise DocumentPageError("Document paths must be normalized and repository-relative.", "document_page_invalid")
    if any(part.casefold().startswith(".env.") or part.casefold() in {".git", ".ssh", ".aws", ".azure"} for part in value.split("/")):
        raise DocumentPageError("Document pages cannot read sensitive configuration sources.", "document_page_invalid")
    return value


def _context_argv(script: Path, arguments: list[str]) -> list[str]:
    if not getattr(sys, "frozen", False):
        return [sys.executable, "-I", "-B", "-X", "utf8", "-c", _CONTEXT_BOOTSTRAP, str(script), *arguments]
    bundled = Path(__file__).resolve().parents[1] / "sdad-engine" / "scripts" / "sdad_context.py"
    if script.resolve(strict=True) != bundled.resolve(strict=True):
        raise DocumentPageError("The frozen Inspector only reads pages through its authenticated bundled engine.")
    return [sys.executable, "--sdad-internal-context", *arguments]


def read_document_page(root: Path, engine: EngineInfo, adapter: ProtocolAdapter,
                       payload: dict[str, Any], *, timeout: float = 10) -> dict[str, Any]:
    if adapter.descriptor.adapter_id != DEFAULT_PROTOCOL_ADAPTER_ID:
        raise UnsupportedContractError("This protocol adapter does not provide document paging.")
    path = _relative(payload.get("path"))
    start, count = payload.get("start", 1), payload.get("lines", 100)
    digest = payload.get("expected_sha256")
    if type(start) is not int or start < 1 or type(count) is not int or not 1 <= count <= MAX_PAGE_LINES:
        raise DocumentPageError("Choose a positive start line and 1–500 lines.", "document_page_invalid")
    if digest is not None and (not isinstance(digest, str) or not _SHA256.fullmatch(digest)):
        raise DocumentPageError("The expected document revision must be a SHA-256 digest.", "document_page_invalid")
    if start > 1 and digest is None:
        raise DocumentPageError("Read the first page before continuing with its document revision.", "document_page_invalid")
    selected = safe_project_path(root, path, purpose="document page", must_exist=True)
    if selected.stat().st_size > MAX_FILE_BYTES:
        raise DocumentPageError("The document exceeds the 1,000,000-byte paged-read budget.")
    state, _ = adapter.load_control_state(root)
    paths = [adapter.descriptor.state_path, adapter.descriptor.todo_path, adapter.descriptor.findings_path,
             (state.get("active_spec") or {}).get("path"), (state.get("current_handoff") or {}).get("path"),
             *(item for item in state.get("routed_docs", []) if item.casefold().endswith(".md"))]
    allowed = set()
    for item in paths:
        if isinstance(item, str):
            try:
                allowed.add(_relative(item))
            except DocumentPageError:
                continue
    if path not in allowed:
        raise DocumentPageError("This document is not in the current project routes.", "document_page_unrouted")
    authenticated = probe_engine(engine.checkout, timeout=timeout)
    if (authenticated.doctor_version, authenticated.revision) != (engine.doctor_version, engine.revision):
        raise DocumentPageError("The selected engine changed; reopen the Inspector before reading pages.")
    script = Path(authenticated.checkout) / "scripts" / "sdad_context.py"
    if not script.is_file() or script.is_symlink():
        raise UnsupportedContractError("This authenticated SDAD release does not include document paging.")
    try:
        script.resolve(strict=True).relative_to(Path(authenticated.checkout))
    except (OSError, RuntimeError, ValueError) as exc:
        raise DocumentPageError("The context helper escapes the authenticated engine.") from exc
    arguments = ["--root", str(root), "read", "--start", str(start), "--lines", str(count)]
    if digest is not None:
        arguments += ["--expect-sha256", digest]
    arguments += ["--", path]
    result = _run(_context_argv(script, arguments), timeout=timeout, cwd=Path(authenticated.checkout))
    if len(result.stdout.encode("utf-8")) > MAX_PAGE_BYTES + 1:
        raise DocumentPageError("The context helper exceeded its output budget.")
    try:
        page = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise DocumentPageError("The context helper returned an unreadable result.") from exc
    if not isinstance(page, dict):
        raise DocumentPageError("The context helper returned an invalid result.")
    if result.returncode != 0:
        message = page.get("error")
        if not isinstance(message, str):
            raise DocumentPageError("The context helper could not read this page.")
        raise DocumentPageError(message, "document_changed" if message.startswith("Source changed;") else "document_page_unavailable")
    lines = page.get("lines")
    if (page.get("schema_version") != 1 or page.get("path") != path
        or not isinstance(page.get("sha256"), str) or not _SHA256.fullmatch(page["sha256"])
        or (digest is not None and page["sha256"] != digest)
        or not isinstance(lines, list) or len(lines) > count or not all(isinstance(line, str) for line in lines)
        or page.get("start") != start or page.get("end") != start + len(lines) - 1
        or type(page.get("file_bytes")) is not int or not 0 <= page["file_bytes"] <= MAX_FILE_BYTES
        or type(page.get("file_lines")) is not int or not 0 <= page["file_lines"] <= MAX_FILE_BYTES
        or type(page.get("page_bytes")) is not int or not 0 <= page["page_bytes"] <= MAX_PAGE_BYTES
        or type(page.get("truncated")) is not bool
        or page.get("next_start") != (page["end"] + 1 if page["truncated"] else None)):
        raise DocumentPageError("The context helper returned an inconsistent page.")
    return {**page, "project_root": str(root)}
