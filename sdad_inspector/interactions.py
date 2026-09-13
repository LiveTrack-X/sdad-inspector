"""Optional, bounded projection of explicit reports; never agent execution evidence."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

KINDS = {"request", "interpretation", "progress", "decision", "response"}
STAGES = {"acknowledged", "planned", "applied", "verification_reported"}
MAX_RECORDS = 100


def _string(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= 4000


def _validate(record: Any) -> None:
    if not isinstance(record, dict) or type(record.get("version")) is not int or record["version"] != 1:
        raise ValueError("unsupported_version")
    if not isinstance(record.get("kind"), str) or record["kind"] not in KINDS:
        raise ValueError("unsupported_kind")
    for key in ("id", "packet", "request_id", "base_revision", "author", "reported_at", "summary"):
        if not _string(record.get(key)):
            raise ValueError("invalid_" + key)
    for key in ("id", "request_id", "packet", "base_revision"):
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,160}", record[key]):
            raise ValueError("invalid_" + key)
    try:
        stamp = datetime.fromisoformat(record["reported_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise ValueError("invalid_reported_at") from None
    if record["kind"] == "request" and not _string(record.get("source_ref")):
        raise ValueError("request_source_required")
    for key in ("scope", "excluded", "assumptions", "remaining", "impact", "alternatives"):
        if key in record and (not isinstance(record[key], list) or len(record[key]) > 30 or not all(_string(x) for x in record[key])):
            raise ValueError("invalid_" + key)
    for key in ("reason", "owner_question", "supersedes", "result_revision"):
        if key in record and not _string(record[key]):
            raise ValueError("invalid_" + key)
    evidence = record.get("evidence", [])
    if not isinstance(evidence, list) or len(evidence) > 30:
        raise ValueError("invalid_evidence")
    for item in evidence:
        if not isinstance(item, dict) or not all(_string(item.get(key)) for key in ("path", "result")):
            raise ValueError("invalid_evidence")
    if record["kind"] == "response":
        if not _string(record.get("correction_id")) or not isinstance(record.get("stage"), str) or record["stage"] not in STAGES:
            raise ValueError("invalid_response")
        if record["stage"] == "verification_reported" and not evidence:
            raise ValueError("verification_evidence_required")
    criteria = record.get("criteria", [])
    if not isinstance(criteria, list) or len(criteria) > 30:
        raise ValueError("invalid_criteria")
    for item in criteria:
        if not isinstance(item, dict) or not _string(item.get("id")) or not _string(item.get("summary")) or not isinstance(item.get("status"), str) or item["status"] not in {"remaining", "implemented_reported", "verification_reported", "blocked"}:
            raise ValueError("invalid_criteria")


def project_interactions(documents: list[dict[str, Any]], *, packet: str | None,
                         project_root: str, read_at: str, truncated: bool = False) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if truncated:
        issues.append({"code": "document_limit", "path": "", "line": 1})
    for doc in documents:
        path = doc["path"]
        content = doc.get("content") or ""
        if doc.get("error"):
            issues.append({"code": "source_unreadable", "path": path, "line": 1})
            continue
        if "<!-- sdad-interactions:1 -->" not in content:
            continue
        if doc.get("error") or doc.get("truncated"):
            issues.append({"code": "source_incomplete", "path": path, "line": 1})
            continue
        content = doc.get("content") or ""
        lines = content.splitlines()
        start = None
        body: list[str] = []
        # Only top-level exact fences are records; never parse examples nested in fences.
        other_fence = None
        for index, line in enumerate(lines, 1):
            if start is None:
                if other_fence:
                    closing = re.fullmatch(r" {0,3}(`{3,}|~{3,})[ \t]*", line)
                    if (closing and closing[1][0] == other_fence[0]
                            and len(closing[1]) >= len(other_fence)):
                        other_fence = None
                    continue
                if line == "```sdad-interaction":
                    start = index
                    body = []
                elif opening := re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line):
                    # Markdown allows up to three spaces before an outer fence.
                    # Backtick info strings cannot themselves contain backticks.
                    if opening[1][0] != "`" or "`" not in opening[2]:
                        other_fence = opening[1]
                continue
            if line != "```":
                body.append(line)
                continue
            source = {"path": path, "line": start, "sha256": hashlib.sha256(content.encode()).hexdigest()}
            try:
                def unique(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result:
                            raise ValueError("duplicate_json_key")
                        result[key] = value
                    return result
                record = json.loads("\n".join(body), object_pairs_hook=unique)
                _validate(record)
                if len(records) >= MAX_RECORDS:
                    raise ValueError("record_limit")
                records.append({**record, "source": source, "link_status": "unresolved"})
            except (ValueError, RecursionError) as exc:
                code = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else "invalid_json"
                issues.append({"code": code[:100], "path": path, "line": start})
            start = None
        if start is not None:
            issues.append({"code": "unterminated_report", "path": path, "line": start})
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(record["id"], []).append(record)
    conflicting = {key for key, group in groups.items() if len(group) != 1}
    requests = [r for r in records if r["kind"] == "request" and r["packet"] == packet]
    for record in records:
        if record["id"] in conflicting or record.get("supersedes") == record["id"]:
            record["link_status"] = "conflict"
        elif record["packet"] != packet:
            record["link_status"] = "other_packet"
        else:
            matches = [r for r in requests if r["request_id"] == record["request_id"]]
            if len(matches) > 1 or any(r["id"] in conflicting for r in matches):
                record["link_status"] = "conflict"
            elif not matches:
                record["link_status"] = "unresolved"
            elif matches[0]["base_revision"] != record["base_revision"]:
                record["link_status"] = "matched" if (record["kind"] == "response" and record.get("stage") in {"applied", "verification_reported"} and record.get("result_revision") == matches[0]["base_revision"]) else "stale"
            else:
                record["link_status"] = "matched"
    # Competing reports are unresolved until explicitly superseded. Never use timestamps.
    for record in records:
        peers = [r for r in records if r["kind"] == record["kind"] and r["request_id"] == record["request_id"] and r["packet"] == record["packet"] and r["base_revision"] == record["base_revision"] and r.get("correction_id") == record.get("correction_id") and r.get("stage") == record.get("stage") and r["link_status"] == "matched"]
        if record["kind"] in {"interpretation", "response"} and len(peers) > 1:
            heads = [r for r in peers if not any(p.get("supersedes") == r["id"] for p in peers)]
            chain: set[str] = set()
            cursor = heads[0] if len(heads) == 1 else None
            while cursor is not None and cursor["id"] not in chain:
                chain.add(cursor["id"])
                previous = cursor.get("supersedes")
                cursor = next((p for p in peers if p["id"] == previous), None)
            resolved = len(heads) == 1 and len(chain) == len(peers)
            for peer in peers:
                peer["link_status"] = "superseded" if resolved and peer is not heads[0] else "matched" if resolved else "conflict"
    return {"schema_version": 1, "project_root": project_root, "packet": packet,
            "observed_at": read_at, "status": "incomplete" if issues else "available" if records else "unreported",
            "records": records, "issues": issues[:100]}
