"""Portable synthetic fixture construction; never operates on a user's project."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


STATE = """version: 2
updated: 2026-09-20
scale: standard
execution_scope: packet
active_spec: SPEC.md
active_packet:
  id: P1
  objective: Shared synthetic receipt contract
  status: in_progress
validation_for: P1
owner_gates: []
validation:
  - command: python check.py
    proves: Selected synthetic behavior
routed_docs: [] # Preserve route comment
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(root):
    return {path.relative_to(root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns, sha256(path.read_bytes()))
            for path in root.rglob("*") if path.is_file()}


def load_corpus(directory, expected_manifest):
    raw = (directory / "manifest.json").read_bytes()
    if sha256(raw) != expected_manifest:
        raise AssertionError("Receipt corpus manifest changed; review and explicitly update its pin.")
    manifest = json.loads(raw)
    if manifest["version"] != 1 or set(manifest["files"]) != {"cases.json", "fixture_helper.py"}:
        raise AssertionError("Unsupported receipt corpus manifest.")
    for name, digest in manifest["files"].items():
        if sha256((directory / name).read_bytes()) != digest:
            raise AssertionError(f"Receipt corpus digest mismatch: {name}")
    corpus = json.loads((directory / "cases.json").read_bytes())
    if corpus["version"] != 1 or len({case["id"] for case in corpus["cases"]}) != len(corpus["cases"]):
        raise AssertionError("Unsupported or duplicate conformance cases.")
    return corpus


def register_text(text, receipt):
    """Fixture-only expected edit; real integration applies Protocol's actual edit."""
    newline = "\r\n" if "\r\n" in text else "\n"
    return text.replace("routed_docs: [] # Preserve route comment" + newline,
                        "routed_docs: # Preserve route comment" + newline + "  - " + json.dumps(receipt, ensure_ascii=False) + newline)


def materialize(root, corpus, case):
    root.mkdir(parents=True, exist_ok=True)
    value = copy.deepcopy(corpus["base_receipt"])
    for address, replacement in case.get("set", {}).items():
        parts = address.split("/")
        target = value
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        target[int(parts[-1]) if isinstance(target, list) else parts[-1]] = replacement
    receipt = case.get("receipt_path", "receipt.json")
    # The corpus may declare unsafe paths. Only harmless synthetic names inside
    # this temporary root are materialized; traversal/device cases stay absent.
    for relative, content in {"source.txt": b"source", "receipt.json.log": b"ok", "SPEC.md": b"# Synthetic specification\n",
                              "docs/TODO-Open-Items.md": b"## Active Work\n", "review-findings.md": b"## Active Findings\n"}.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for relative in case.get("synthetic_dirs", []):
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in case.get("synthetic_files", []):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"synthetic fixture, not a credential")
    if case.get("source_content") is not None:
        (root / "source.txt").write_bytes(case["source_content"].encode("utf-8"))
    if case.get("missing_source"):
        (root / "source.txt").unlink()
    if case.get("missing_log"):
        (root / "receipt.json.log").unlink()
    raw = case.get("raw_receipt", json.dumps(value, ensure_ascii=False)).encode("utf-8")
    size = case.get("receipt_bytes")
    if size:
        assert len(raw) <= size
        raw += b" " * (size - len(raw))
    if not case.get("absent_receipt"):
        target = root / receipt
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    text = STATE
    if case.get("registered"):
        text = register_text(text, receipt)
    proposed_delta = len(register_text(text, receipt).encode("utf-8")) - len(text.encode("utf-8"))
    if "state_lines" in case:
        text += "# pad\n" * (case["state_lines"] - len(text.splitlines()))
    target_bytes = case.get("state_bytes")
    if "proposed_state_bytes" in case:
        target_bytes = case["proposed_state_bytes"] - proposed_delta
    if target_bytes:
        padding = target_bytes - len(text.encode("utf-8"))
        assert padding >= 2
        text += "#" + "x" * (padding - 2) + "\n"
    if case.get("state_version"):
        text = text.replace("version: 2", "version: " + str(case["state_version"]))
    if case.get("crlf"):
        text = text.replace("\n", "\r\n")
    (root / "sdad-state.yaml").write_bytes(text.encode("utf-8"))
    return value, receipt


def apply_preview(root, preview):
    """Apply an actual, hash-pinned Protocol suggestion in a temporary fixture."""
    path = root / "sdad-state.yaml"
    raw = path.read_bytes()
    if sha256(raw) != preview["state_sha256"]:
        raise AssertionError("Refusing a stale preview.")
    if preview["registration"] == "already_registered":
        if preview["suggestion"] is not None:
            raise AssertionError("Registered receipt unexpectedly has a suggestion.")
        return
    edit = preview["suggestion"]
    lines = raw.decode("utf-8").splitlines(keepends=True)
    index, count = edit["start_line"] - 1, edit["delete_count"]
    if index < 0 or count != 1 or lines[index:index + count] != edit["expected_lines"]:
        raise AssertionError("Preview lines no longer match the original state.")
    proposed = "".join(lines[:index] + edit["replacement_lines"] + lines[index + count:]).encode("utf-8")
    if len(proposed) > 65536 or len(proposed.decode("utf-8").splitlines()) > 500:
        raise AssertionError("Preview proposed state outside Inspector's budget.")
    path.write_bytes(proposed)
