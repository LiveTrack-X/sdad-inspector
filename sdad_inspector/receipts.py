"""Read explicitly routed, unsigned verification receipts; never execute commands."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .errors import InspectorError
from .paths import MAX_CONTROL_BYTES, MAX_CONTROL_LINES, _is_sensitive, safe_project_path
from .state import SUPPORTED_STATE_SCHEMAS, _load_yaml, load_control_state

SCHEMA = "sdad.verification-receipt"
MAX_RECEIPTS = 10
MAX_RECEIPT_BYTES = 64 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 16 * 1024 * 1024
MAX_LOG_BYTES = 64 * 1024
OUTCOMES = {"passed", "failed", "timeout", "start_failed", "interrupted"}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_DEVICES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


class ReceiptNavigationError(InspectorError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def _text(value: Any, maximum: int = 1024) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum and "\x00" not in value


def _path(value: Any) -> bool:
    return (_text(value) and not any(c in value for c in ("\\", ":")) and not value.startswith("/")
            and not any(part.casefold() in {"", ".", "..", ".git"} or part.casefold().startswith(".env")
                        or part.endswith((".", " ")) or part.split(".")[0].casefold() in _DEVICES
                        or any(ord(char) < 32 or char in '<>"|?*' for char in part) for part in value.split("/")))


def _keys(value: Any, names: str) -> bool:
    return isinstance(value, dict) and set(value) == set(names.split())


def _identity(value: Any) -> bool:
    return value is None or (_keys(value, "sha256 size") and isinstance(value["sha256"], str) and bool(_SHA.fullmatch(value["sha256"])) and type(value["size"]) is int and 0 <= value["size"] <= MAX_SOURCE_BYTES)


def _timestamp(value: Any) -> bool:
    try:
        return isinstance(value, str) and value.endswith("Z") and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate receipt field.")
        result[key] = value
    return result


def validate_receipt(value: Any) -> dict:
    """Strict optional v1 envelope, independent of State v2 and Doctor schemas."""
    if not _keys(value, "schema version id packet requirement scope cwd command started_at ended_at outcome exit_code source_stability sources log limits") or value["schema"] != SCHEMA or type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("Unsupported or incomplete verification receipt.")
    if any(not _text(value[key]) for key in ("id", "packet", "requirement", "scope")) or not (value["cwd"] == "." or _path(value["cwd"])):
        raise ValueError("Invalid receipt identity or scope.")
    command = value["command"]
    if not _keys(command, "argv platform python_version") or not _text(command["platform"]) or not _text(command["python_version"]) or not isinstance(command["argv"], list) or not 1 <= len(command["argv"]) <= 128 or any(not isinstance(arg, str) or "\x00" in arg for arg in command["argv"]) or not command["argv"][0] or sum(len(arg) for arg in command["argv"]) > 8192:
        raise ValueError("Invalid command metadata.")
    if not _timestamp(value["started_at"]) or not _timestamp(value["ended_at"]):
        raise ValueError("Invalid observation timestamps.")
    outcome = value["outcome"]
    code = value["exit_code"]
    if not isinstance(outcome, str) or outcome not in OUTCOMES or not (code is None or type(code) is int):
        raise ValueError("Invalid execution outcome.")
    if (outcome == "passed" and code != 0) or (outcome == "failed" and (code is None or code == 0)) or (outcome not in {"passed", "failed"} and code is not None):
        raise ValueError("Outcome and exit code disagree.")
    sources = value["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
        raise ValueError("Invalid source list.")
    for source in sources:
        if not _keys(source, "path before after error") or not _path(source["path"]) or not _identity(source["before"]) or not _identity(source["after"]) or not (source["error"] is None or _text(source["error"])):
            raise ValueError("Invalid source observation.")
        if (source["before"] is None or source["after"] is None) and source["error"] is None:
            raise ValueError("Missing source identity must have a limit.")
    if len({s["path"].casefold() for s in sources}) != len(sources):
        raise ValueError("Duplicate source path.")
    stability = "changed" if any(s["before"] is not None and s["after"] is not None and s["before"] != s["after"] for s in sources) else "unknown" if any(s["error"] for s in sources) else "stable"
    if value["source_stability"] != stability:
        raise ValueError("Source stability contradicts observations.")
    log = value["log"]
    if not _keys(log, "path sha256 bytes total_bytes truncated complete") or not _path(log["path"]) or not isinstance(log["sha256"], str) or not _SHA.fullmatch(log["sha256"]):
        raise ValueError("Invalid log identity.")
    if type(log["bytes"]) is not int or not 0 <= log["bytes"] <= MAX_LOG_BYTES or type(log["total_bytes"]) is not int or log["total_bytes"] < log["bytes"] or type(log["truncated"]) is not bool or type(log["complete"]) is not bool or log["truncated"] != (log["total_bytes"] > log["bytes"]):
        raise ValueError("Invalid log bounds.")
    if not isinstance(value["limits"], list) or len(value["limits"]) > 12 or any(not _text(item) for item in value["limits"]):
        raise ValueError("Invalid claim limits.")
    return value


def _read(root: Path, relative: str, maximum: int) -> bytes:
    if not _path(relative):
        raise ValueError("Unsafe receipt path.")
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if hasattr(cursor, "is_junction") and cursor.is_junction():
            raise ValueError("Junctions are not receipt evidence paths.")
    path = safe_project_path(root, relative, purpose="verification receipt evidence", must_exist=True)
    if path.stat().st_size > maximum:
        raise ValueError("Evidence read budget exceeded.")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        data = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    if len(data) > maximum:
        raise ValueError("Evidence read budget exceeded.")
    current = safe_project_path(root, relative, purpose="verification receipt evidence", must_exist=True).stat()
    if any((item.st_ino, item.st_size, item.st_mtime_ns) != (before.st_ino, before.st_size, before.st_mtime_ns) for item in (after, current)):
        raise ValueError("Evidence changed while reading.")
    return data



def _inspect_receipt(root: Path, relative: str, budget: int) -> tuple[dict[str, Any], int]:
    result = {"path": relative, "receipt": None, "source_match": "unknown", "log_match": "unknown", "sources": [], "error": None}
    try:
        value = validate_receipt(json.loads(_read(root, relative, MAX_RECEIPT_BYTES).decode("utf-8"), object_pairs_hook=_no_duplicates))
        result["receipt"] = value
        if value["log"]["path"] == relative or value["log"]["path"] in {s["path"] for s in value["sources"]} or relative in {s["path"] for s in value["sources"]}:
            raise ValueError("Receipt, log and sources must be distinct.")
        for source in value["sources"]:
            comparison = {"path": source["path"], "match": "unknown", "reason": None}
            try:
                if budget <= 0:
                    raise ValueError("Total source comparison budget exceeded.")
                allowance = min(MAX_SOURCE_BYTES, budget)
                # A read that later fails its identity check still consumed
                # bytes. Reserve its allowance, refund only a successful read.
                budget -= allowance
                data = _read(root, source["path"], allowance)
                budget += allowance - len(data)
                current = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
                if source["before"] is None or source["after"] is None or source["error"]:
                    comparison["reason"] = "receipt_source_incomplete"
                elif source["before"] != source["after"]:
                    comparison.update(match="changed", reason="changed_during_run")
                elif current == source["after"]:
                    comparison.update(match="matched", reason="declared_bytes_match")
                else:
                    comparison.update(match="changed", reason="changed_since_run")
            except (OSError, ValueError, RuntimeError, InspectorError):
                comparison["reason"] = "source_unreadable_unsafe_or_over_budget"
            result["sources"].append(comparison)
        result["source_match"] = "changed" if any(s["match"] == "changed" for s in result["sources"]) else "unknown" if any(s["match"] == "unknown" for s in result["sources"]) else "matched"
        try:
            log = value["log"]
            data = _read(root, log["path"], MAX_LOG_BYTES)
            result["log_match"] = "matched" if len(data) == log["bytes"] and hashlib.sha256(data).hexdigest() == log["sha256"] else "changed"
        except (OSError, ValueError, RuntimeError, InspectorError):
            result["log_match"] = "unknown"
    except (OSError, ValueError, RuntimeError, InspectorError, RecursionError):
        result.update(receipt=None, source_match="unknown", log_match="unknown", error="Receipt missing, unsafe, oversized, malformed or unsupported.")
    return result, budget


def load_verification_receipts(root: Path, *, state: dict | None = None) -> dict[str, Any]:
    """Only JSON paths explicitly named in routed_docs are eligible; no project writes."""
    root = root.resolve(strict=True)
    if state is None:
        state, _ = load_control_state(root)
    routes = list(dict.fromkeys(path for path in state.get("routed_docs", []) if isinstance(path, str) and path.casefold().endswith(".json")))
    results = []
    budget = MAX_TOTAL_SOURCE_BYTES
    for relative in routes[:MAX_RECEIPTS]:
        result, budget = _inspect_receipt(root, relative, budget)
        results.append(result)
    return {"project_root": str(root), "packet": (state.get("active_packet") or {}).get("id"),
            "read_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "receipts": results, "truncated": len(routes) > MAX_RECEIPTS}


def _registered_path(value: Any) -> bool:
    return (_path(value) and value.casefold().endswith(".json")
            and not any(_is_sensitive(part) for part in value.split("/")))


def _route_index(root: Path) -> tuple[dict[str, Any], list[str]]:
    """Read only bounded state bytes, never receipt, log or source metadata/content."""
    try:
        root = root.resolve(strict=True)
        data = _read(root, "sdad-state.yaml", MAX_CONTROL_BYTES)
        text = data.decode("utf-8")
        if len(text.splitlines()) > MAX_CONTROL_LINES:
            raise ValueError("State exceeds the line budget.")
        state = _load_yaml(text)
        if type(state.get("version")) is not int or state["version"] not in SUPPORTED_STATE_SCHEMAS:
            raise ValueError("Unsupported state schema.")
        packet = state.get("active_packet")
        if not isinstance(packet, dict) or not _text(packet.get("id")):
            raise ValueError("Current packet is unavailable.")
        routed = state.get("routed_docs")
        if routed is None:
            routed = []
        if not isinstance(routed, list) or any(not isinstance(item, str) for item in routed):
            raise ValueError("Receipt routes are unavailable.")
        routes = list(dict.fromkeys(path for path in routed if _registered_path(path)))
        # Raw state bytes also pin non-route changes; neither receipt packet names
        # nor their validity are inferred from filenames or the current packet.
        identity = {"project_root": str(root), "state_sha256": hashlib.sha256(data).hexdigest(),
                    "packet": packet["id"], "paths": routes}
        revision = hashlib.sha256(json.dumps(identity, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()
        return {"version": 1, "project_root": str(root), "packet": packet["id"],
                "read_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "revision": revision}, routes
    except (OSError, ValueError, RuntimeError, InspectorError, RecursionError) as exc:
        raise ReceiptNavigationError("Receipt routes could not be read safely from the current state.",
                                     "receipt_navigation_unavailable") from exc


def _check_revision(revision: Any, current: str, *, required: bool) -> None:
    if revision is None and not required:
        return
    if not isinstance(revision, str) or not _SHA.fullmatch(revision):
        raise ReceiptNavigationError("A valid receipt route revision is required.", "receipt_navigation_invalid")
    if revision != current:
        raise ReceiptNavigationError("Receipt routes or the current packet changed; reload the list.",
                                     "receipt_navigation_changed")


def list_verification_receipts(root: Path, *, offset: Any = 0, revision: Any = None) -> dict[str, Any]:
    if type(offset) is not int or offset < 0:
        raise ReceiptNavigationError("Receipt offset must be a non-negative integer.", "receipt_navigation_invalid")
    result, routes = _route_index(root)
    _check_revision(revision, result["revision"], required=offset > 0)
    if offset > len(routes):
        raise ReceiptNavigationError("Receipt offset exceeds the registered list.", "receipt_navigation_invalid")
    end = min(offset + MAX_RECEIPTS, len(routes))
    return {**result, "offset": offset, "total": len(routes),
            "next_offset": end if end < len(routes) else None, "paths": routes[offset:end]}


def inspect_verification_receipt(root: Path, *, path: Any, revision: Any) -> dict[str, Any]:
    if not _registered_path(path):
        raise ReceiptNavigationError("A safe registered JSON receipt path is required.", "receipt_navigation_invalid")
    result, routes = _route_index(root)
    _check_revision(revision, result["revision"], required=True)
    if path not in routes:
        raise ReceiptNavigationError("This receipt is not registered in the current routes.",
                                     "receipt_navigation_unregistered")
    observation, _ = _inspect_receipt(root.resolve(strict=True), path, MAX_TOTAL_SOURCE_BYTES)
    # An external editor can change state while source comparison runs. Do not
    # return the observation under the earlier registration/packet declaration.
    current, _ = _route_index(root)
    _check_revision(result["revision"], current["revision"], required=True)
    return {**result, "read_at": current["read_at"], "observation": observation}
