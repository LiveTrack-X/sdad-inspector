"""Exercise a packaged Inspector's authenticated receipt API on a disposable fixture."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener


def fixture(root: Path) -> None:
    root.mkdir()
    (root / "docs").mkdir()
    (root / "SPEC").mkdir()
    (root / "evidence").mkdir()
    (root / "source.txt").write_bytes(b"portable receipt fixture\n")
    identity = {"size": (root / "source.txt").stat().st_size,
                "sha256": hashlib.sha256(b"portable receipt fixture\n").hexdigest()}
    routes = [f"evidence/run{index:02d}.json" for index in range(1, 12)]
    (root / "sdad-state.yaml").write_text(
        "version: 2\nupdated: 2026-09-20\nscale: standard\nexecution_scope: packet\n"
        "active_spec: SPEC/SPEC-COMPLETE.md\nactive_packet:\n  id: portable-smoke\n"
        "  objective: Inspect a synthetic receipt fixture\n  status: in_progress\n"
        "validation_for: portable-smoke\nowner_gates: []\nvalidation:\n"
        "  - command: python -V\n    proves: Fixture declaration only\nrouted_docs:\n"
        + "".join("  - " + path + "\n" for path in routes), encoding="utf-8")
    (root / "SPEC/SPEC-COMPLETE.md").write_text("# Portable smoke\n\nSynthetic fixture only.\n", encoding="utf-8")
    (root / "docs/INDEX.md").write_text("# Project Documentation Router\n\nStatus: Active\n", encoding="utf-8")
    (root / "docs/TODO-Open-Items.md").write_text("# Open Implementation Items\n\nStatus: Active\n\n## Active Work\n\n- [ ] [packet:portable-smoke] [current] [phase:Verify] Read the fixture.\n", encoding="utf-8")
    (root / "review-findings.md").write_text("# Review Findings\n\nStatus: Active\n\n## Active Findings\n\nNone.\n", encoding="utf-8")
    for index, path in enumerate(routes):
        log = path + ".log"
        (root / log).write_bytes(b"")
        value = {"schema": "sdad.verification-receipt", "version": 1, "id": f"synthetic-{index}",
                 "packet": "portable-smoke", "requirement": "Synthetic fixture", "scope": "No validation command was executed to create this fixture", "cwd": ".",
                 "command": {"argv": ["fixture-only"], "python_version": "fixture", "platform": "fixture"},
                 "started_at": "2026-09-20T00:00:00Z", "ended_at": "2026-09-20T00:00:00Z",
                 "outcome": "passed", "exit_code": 0, "source_stability": "stable",
                 "sources": [{"path": "source.txt", "before": identity, "after": identity, "error": None}],
                 "log": {"path": log, "sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0, "total_bytes": 0, "truncated": False, "complete": True},
                 "limits": ["Synthetic test data, not a real verification run."]}
        (root / path).write_text(json.dumps(value), encoding="utf-8")
    (root / routes[0]).write_text("{deliberately malformed fixture", encoding="utf-8")


def fingerprint(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def check_api(origin: str, project: Path, token: str, *, opener=None) -> list[str]:
    opener = opener or build_opener(ProxyHandler({}))
    def request(path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = Request(origin + path, data=data, headers={"Origin": origin, "X-SDAD-Session": token, "Content-Type": "application/json"})
        with opener.open(req, timeout=10) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Smoke response exceeded limit")
        return json.loads(raw)
    snapshot = request("/api/snapshot")
    root = str(project.resolve())
    if snapshot["project"]["root"] != root or snapshot["state"]["active_packet"]["id"] != "portable-smoke" or snapshot["inspection_status"] != "completed":
        raise ValueError("The packaged project observation is not the expected completed fixture")
    page = request("/api/verification-receipt-list", {"project_root": root})
    if page["total"] != 11 or len(page["paths"]) != 10 or page["next_offset"] != 10:
        raise ValueError("The packaged first receipt page is incomplete")
    bad = request("/api/verification-receipt-inspect", {"project_root": root, "path": page["paths"][0], "revision": page["revision"]})["observation"]
    if bad["receipt"] is not None or not bad["error"]:
        raise ValueError("The packaged reader accepted a malformed receipt")
    later = request("/api/verification-receipt-list", {"project_root": root, "offset": 10, "revision": page["revision"]})
    if later["paths"] != ["evidence/run11.json"] or later["next_offset"] is not None:
        raise ValueError("The packaged reader cannot reach the eleventh receipt")
    selected = request("/api/verification-receipt-inspect", {"project_root": root, "path": later["paths"][0], "revision": page["revision"]})["observation"]
    if selected["error"] or selected["source_match"] != "matched" or selected["log_match"] != "matched" or selected["receipt"]["packet"] != "portable-smoke":
        raise ValueError("The packaged selected receipt does not match its fixture")
    return ["completed_project_observation", "first_page_10_of_11", "malformed_receipt_rejected", "eleventh_receipt_source_and_log_match"]


def smoke_receipts(executable: Path, *, seconds: float = 2, timeout: float = 60) -> dict:
    with tempfile.TemporaryDirectory(prefix="sdad-portable-receipts-") as raw:
        temp = Path(raw).resolve()
        project = temp / "프로젝트 with spaces"
        fixture(project)
        before = fingerprint(project)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        duration = max(seconds, 8)
        argv = [str(executable), str(project), "--hidden", "--port", str(port), "--smoke-seconds", str(duration), "--smoke-preferences", str(temp / "app/preferences.json")]
        environment = os.environ.copy()
        environment.pop("PYTHONHOME", None)
        environment.pop("PYTHONPATH", None)
        process = subprocess.Popen(argv, cwd=temp, env=environment, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        checks = []
        error = None
        timed_out = False
        deadline = time.monotonic() + timeout
        try:
            opener = build_opener(ProxyHandler({}))
            token = None
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with opener.open(origin + "/", timeout=1) as response:
                        html = response.read(256 * 1024).decode("utf-8")
                    match = re.search(r'<meta name="sdad-session" content="([^"<>]+)"', html)
                    if match:
                        token = match.group(1)
                        break
                except (OSError, URLError):
                    pass
                time.sleep(0.1)
            if token is None:
                raise ValueError("Packaged loopback page did not become ready")
            checks = check_api(origin, project, token, opener=opener)
            process.communicate(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            error = "Packaged smoke exceeded its deadline"
        except Exception as exc:
            error = str(exc)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
        unchanged = fingerprint(project) == before
        exit_code = process.returncode
        if not unchanged:
            error = "Packaged inspection changed the project fixture"
        return {"artifact": str(executable), "exit_code": 0 if exit_code == 0 and not error else (exit_code or 1),
                "native_exit_code": exit_code, "bounded_seconds": duration, "timed_out": timed_out,
                "checks": checks, "fixture_unchanged": unchanged, "error": error,
                "scope": "Actual packaged loopback APIs and bounded native window lifecycle; not native visual interaction or user acceptance"}
