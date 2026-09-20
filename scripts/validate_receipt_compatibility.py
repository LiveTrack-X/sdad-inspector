#!/usr/bin/env python3
"""Offline, checkout-only conformance of Protocol preview and Inspector reads."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "verification-receipts"
MANIFEST_SHA256 = "852e3277648ee0a93cdb17b6fdd020443b19112450968a98f86455d926ada8d0"
sys.path.insert(0, str(ROOT))

from sdad_inspector.receipts import (ReceiptNavigationError, _no_duplicates, inspect_verification_receipt,
                                     list_verification_receipts, load_verification_receipts, validate_receipt)


def verify_corpus(directory):
    raw = (directory / "manifest.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256, "Receipt corpus manifest pin mismatch")
    manifest = json.loads(raw)
    require(manifest["version"] == 1 and set(manifest["files"]) == {"cases.json", "fixture_helper.py"}, "Unsupported corpus manifest")
    for name, digest in manifest["files"].items():
        require(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, "Receipt corpus digest mismatch: " + name)


def load_fixture():
    # Verify executable helper bytes before importing any copied fixture code.
    verify_corpus(CORPUS)
    spec = importlib.util.spec_from_file_location("receipt_corpus_fixture", CORPUS / "fixture_helper.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    return fixture, fixture.load_corpus(CORPUS, MANIFEST_SHA256)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_reader(fixture, corpus, case, root, *, already_registered=False):
    value, path = fixture.materialize(root, corpus, case) if not already_registered else (None, case.get("receipt_path", "receipt.json"))
    raw = (root / path).read_bytes()
    try:
        decoded = validate_receipt(json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates))
    except (ValueError, RecursionError):
        require(not case["schema_valid"], "Reader rejected an expected valid schema")
    else:
        require(case["schema_valid"], "Reader accepted an invalid schema")
        value = decoded
    expected = case["reader"]
    state_path = root / "sdad-state.yaml"
    if not already_registered and expected not in {"state_unavailable", "unregistered"}:
        state_path.write_bytes(fixture.register_text(state_path.read_bytes().decode("utf-8"), path).encode("utf-8"))
    before = fixture.fingerprint(root)
    try:
        if expected == "state_unavailable":
            try:
                list_verification_receipts(root)
            except ReceiptNavigationError as exc:
                require(exc.code == "receipt_navigation_unavailable", "Unavailable state lost its error distinction")
            else:
                raise AssertionError("Unbounded/unsupported state was accepted")
            return
        page = list_verification_receipts(root)
        require(page["packet"] == "P1", "Current packet label changed")
        if expected in {"unregistered", "unlisted"}:
            require(path not in page["paths"], "Unsafe/unregistered receipt became eligible")
            try:
                inspect_verification_receipt(root, path=path, revision=page["revision"])
            except ReceiptNavigationError as exc:
                require(exc.code in {"receipt_navigation_invalid", "receipt_navigation_unregistered"}, "Wrong selection rejection")
            else:
                raise AssertionError("Unsafe/unregistered selection was accepted")
            return
        require(path in page["paths"], "Registered receipt is missing from list")
        observation = inspect_verification_receipt(root, path=path, revision=page["revision"])["observation"]
        legacy = load_verification_receipts(root)
        require(set(legacy) == {"project_root", "packet", "read_at", "receipts", "truncated"}, "Legacy response keys changed")
        require(legacy["receipts"] == [observation], "Legacy and selected observations disagree")
        if expected == "malformed":
            require(observation["receipt"] is None and observation["error"] and observation["source_match"] == "unknown", "Malformed receipt became a success")
        else:
            require(observation["source_match"] == expected, "Wrong current source comparison")
            require(observation["log_match"] == case.get("log_match", "matched"), "Wrong retained-log comparison")
            require(observation["receipt"] == value, "Outcome, historical packet or capture limits were changed")
    finally:
        require(fixture.fingerprint(root) == before, "Reader changed the inspected fixture")


def preview_cli(protocol, fixture, root, path):
    before = fixture.fingerprint(root)
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(protocol / "scripts" / "sdad_evidence.py"),
                             "--project", str(root), "--preview-connection", path],
                            capture_output=True, text=True, encoding="utf-8", timeout=15, cwd=protocol)
    require(fixture.fingerprint(root) == before, "Protocol preview wrote to the inspected fixture")
    return result


def run_checks(protocol_checkout=None):
    fixture, corpus = load_fixture()
    protocol = None
    if protocol_checkout is not None:
        protocol = Path(protocol_checkout).resolve(strict=True)
        require((protocol / "scripts" / "sdad_evidence.py").is_file(), "Explicit Protocol checkout has no collector")
        authoritative = protocol / "tests" / "fixtures" / "verification-receipts"
        verify_corpus(authoritative)
        for name in ("manifest.json", "cases.json", "fixture_helper.py"):
            require((CORPUS / name).read_bytes() == (authoritative / name).read_bytes(), "Protocol/Inspector corpus copy drift: " + name)
    results = []
    for case in corpus["cases"]:
        try:
            with tempfile.TemporaryDirectory(prefix="sdad-receipt-conformance-") as directory:
                check_reader(fixture, corpus, case, Path(directory).resolve())
            if protocol is not None:
                with tempfile.TemporaryDirectory(prefix="sdad-preview-reader-") as directory:
                    root = Path(directory).resolve()
                    value, path = fixture.materialize(root, corpus, case)
                    result = preview_cli(protocol, fixture, root, path)
                    if case["preview"] == "reject":
                        require(result.returncode == 2 and not result.stdout.strip(), "Invalid preview did not reject without proposal")
                    else:
                        require(result.returncode == 0, "Valid preview failed: " + result.stderr[-2000:])
                        preview = json.loads(result.stdout)
                        require(preview["current_packet"] == "P1" and preview["receipt_packet"] == value["packet"], "Preview relabeled a packet")
                        require(preview["receipt_sha256"] == fixture.sha256((root / path).read_bytes()), "Preview receipt identity changed")
                        fixture.apply_preview(root, preview)
                        check_reader(fixture, corpus, case, root, already_registered=True)
                        again = preview_cli(protocol, fixture, root, path)
                        require(again.returncode == 0 and json.loads(again.stdout)["registration"] == "already_registered"
                                and json.loads(again.stdout)["suggestion"] is None, "Preview is not idempotent")
            results.append({"case": case["id"], "status": "passed"})
        except (AssertionError, ValueError, OSError, ReceiptNavigationError, subprocess.TimeoutExpired) as exc:
            results.append({"case": case["id"], "status": "failed", "reason": str(exc)})
    return {"version": 1, "manifest_sha256": MANIFEST_SHA256, "protocol_preview_executed": protocol is not None,
            "cases": results, "passed": sum(item["status"] == "passed" for item in results),
            "failed": sum(item["status"] == "failed" for item in results),
            "limits": ["Synthetic cross-checkout observations, not user productivity or release acceptance.",
                       "No network fetch or application runtime dependency; only the explicit local Protocol checkout is invoked."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-checkout", type=Path, help="Explicit trusted local Protocol source checkout; never fetched")
    args = parser.parse_args(argv)
    try:
        result = run_checks(args.protocol_checkout)
    except (AssertionError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
