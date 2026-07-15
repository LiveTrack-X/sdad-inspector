#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PROJECT = ROOT / "tests" / "fixture-projects" / "state-v2"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdad_inspector.preferences import RecentProjectsStore  # noqa: E402
from sdad_inspector.server import InspectorService, create_server  # noqa: E402

EXCLUDED_PARTS = {
    ".git",
    ".runtime",
    ".npm-cache",
    "node_modules",
    "dist",
    "__pycache__",
}


def project_fingerprint(project_root: Path) -> dict[str, tuple[int, int, str]]:
    result: dict[str, tuple[int, int, str]] = {}
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        stat = path.stat()
        result[relative.as_posix()] = (
            stat.st_size,
            stat.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return result


def request(
    server,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    origin: str | None = None,
    body: dict[str, object] | None = None,
    host: str | None = None,
) -> tuple[int, dict[str, str], bytes]:
    address, port = server.server_address[:2]
    connection = http.client.HTTPConnection(address, port, timeout=10)
    headers: dict[str, str] = {"Host": host or server.authority}
    if token is not None:
        headers["X-SDAD-Session"] = token
    if origin is not None:
        headers["Origin"] = origin
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    connection.request(method, path, body=data, headers=headers)
    response = connection.getresponse()
    payload = response.read()
    result = response.status, dict(response.headers.items()), payload
    connection.close()
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the loopback browser contract.")
    parser.add_argument(
        "--sdad-checkout",
        type=Path,
        default=ROOT / ".runtime" / "sdad-v3.2.2",
        help="Path to a clean authenticated SDAD v3.2.2 checkout.",
    )
    args = parser.parse_args(argv)
    engine = args.sdad_checkout.resolve()
    web = ROOT / "web" / "dist"
    require(engine.is_dir(), "Clean v3.2.2 runtime archive is missing.")
    require((web / "index.html").is_file(), "Run npm --prefix web run build first.")
    require(FIXTURE_PROJECT.is_dir(), "Synthetic state-v2 fixture project is missing.")
    project_data = tempfile.TemporaryDirectory(prefix="sdad-inspector-project-")
    project_root = (Path(project_data.name) / "project").resolve()
    shutil.copytree(FIXTURE_PROJECT, project_root)
    before = project_fingerprint(project_root)
    app_data = tempfile.TemporaryDirectory(prefix="sdad-inspector-contract-")
    service = InspectorService(
        project_root,
        engine,
        project_picker=lambda _initial: None,
        clipboard_reader=lambda: f'"{project_root}"',
        preferences_store=RecentProjectsStore(Path(app_data.name) / "preferences.json"),
        rule_export_picker=lambda _suggested: None,
    )
    token = "browser-contract-session"
    server = create_server(service, web, session_token=token)
    require(server.server_address[0] == "127.0.0.1", "Server did not bind to loopback.")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, headers, index = request(server, "/")
        require(status == 200, "Index route failed.")
        require(token.encode("ascii") in index, "Session token was not injected into index.")
        require(b"__SDAD_SESSION_TOKEN__" not in index, "Session placeholder leaked.")
        require("default-src 'self'" in headers.get("Content-Security-Policy", ""), "CSP is missing.")
        require("Access-Control-Allow-Origin" not in headers, "CORS was enabled unexpectedly.")

        denied, _, _ = request(server, "/api/snapshot")
        require(denied == 403, "Snapshot route accepted a missing token.")
        progress_denied, _, _ = request(server, "/api/progress")
        require(progress_denied == 403, "Progress route accepted a missing token.")
        invalid_host, _, _ = request(
            server, "/api/snapshot", token=token, host="evil.invalid"
        )
        require(invalid_host == 400, "Host header protection failed.")

        snapshot_status, api_headers, snapshot_body = request(
            server, "/api/snapshot", token=token
        )
        require(snapshot_status == 200, "Authenticated snapshot route failed.")
        snapshot = json.loads(snapshot_body)
        require(snapshot["read_only"] is True, "Snapshot lost its read-only marker.")
        require(snapshot["doctor"]["exit_code"] in {0, 1, 2}, "Doctor exit code was lost.")
        require(api_headers.get("Cache-Control") == "no-store", "API caching is not disabled.")

        documents_status, documents_headers, documents_body = request(
            server, "/api/documents", token=token
        )
        require(documents_status == 200, "Authenticated live-document route failed.")
        documents = json.loads(documents_body)
        allowed_paths = {
            snapshot["state"]["active_spec"]["path"],
            "docs/TODO-Open-Items.md",
            "review-findings.md",
            *snapshot["state"]["routed_docs"],
        }
        require(
            all(item["path"] in allowed_paths for item in documents["documents"]),
            "Live-document route escaped declared Markdown paths.",
        )
        require(documents_headers.get("Cache-Control") == "no-store", "Live documents are cacheable.")

        activity_status, activity_headers, activity_body = request(
            server, "/api/activity", token=token
        )
        require(activity_status == 200, "Authenticated activity route failed.")
        activity = json.loads(activity_body)
        require(activity["project_root"] == str(project_root), "Activity route crossed the project boundary.")
        require(len(activity["files"]) <= 160, "Activity path history exceeded its bound.")
        require(len(activity["commits"]) <= 20, "Commit history exceeded its bound.")
        require(all("author" not in commit for commit in activity["commits"]), "Commit author identity leaked.")
        require(activity_headers.get("Cache-Control") == "no-store", "Activity response is cacheable.")

        recent_status, recent_headers, recent_body = request(
            server, "/api/recent-projects", token=token
        )
        require(recent_status == 200, "Authenticated recent-project route failed.")
        require(json.loads(recent_body)["recent_projects"] == [], "Recent-project contract was not isolated.")
        require(recent_headers.get("Cache-Control") == "no-store", "Recent projects are cacheable.")

        rule5_status, rule5_headers, rule5_body = request(
            server, "/api/rule5-candidates", token=token
        )
        require(rule5_status == 200, "Authenticated Rule 5 candidate route failed.")
        rule5 = json.loads(rule5_body)
        require(rule5["source_path"] == "review-findings.md", "Rule 5 source escaped the fixed finding route.")
        require(rule5_headers.get("Cache-Control") == "no-store", "Rule 5 candidates are cacheable.")

        missing_rule5_origin, _, _ = request(
            server,
            "/api/rule5/preview",
            method="POST",
            token=token,
            body={},
        )
        require(missing_rule5_origin == 403, "Rule 5 preview accepted a missing Origin.")
        complete_candidate = next(
            (item for item in rule5["candidates"] if item["complete"] is True),
            None,
        )
        if complete_candidate is not None:
            preview_status, _, preview_body = request(
                server,
                "/api/rule5/preview",
                method="POST",
                token=token,
                origin=server.origin,
                body=complete_candidate,
            )
            require(preview_status == 200, "Rule 5 Markdown preview failed.")
            preview = json.loads(preview_body)
            require(preview["markdown"].startswith("# Rule 5 Proposal:"), "Rule 5 preview is not Markdown.")
            cancel_status, _, cancel_body = request(
                server,
                "/api/rule5/export",
                method="POST",
                token=token,
                origin=server.origin,
                body={**complete_candidate, "confirmed": True, "preview_sha256": preview["sha256"]},
            )
            require(cancel_status == 200, "Rule 5 cancelled Save As route failed.")
            cancelled = json.loads(cancel_body)
            require(cancelled["cancelled"] is True and cancelled["saved"] is False, "Rule 5 cancel created a save claim.")
            rule5_observation = "cancelled proposal export"
        elif rule5["candidates"]:
            blocked_status, _, _ = request(
                server,
                "/api/rule5/preview",
                method="POST",
                token=token,
                origin=server.origin,
                body=rule5["candidates"][0],
            )
            require(blocked_status == 422, "Incomplete Rule 5 candidate was not blocked.")
            rule5_observation = "incomplete proposal blocked"
        else:
            rule5_observation = "closed ledger returned no active proposal"

        picker_status, _, picker_body = request(
            server,
            "/api/project-picker",
            method="POST",
            token=token,
            origin=server.origin,
            body={"initial_path": str(project_root)},
        )
        require(picker_status == 200, "Explicit folder-picker route failed.")
        require(json.loads(picker_body)["selected"] is False, "Picker cancel was not preserved.")
        paste_status, _, paste_body = request(
            server,
            "/api/clipboard/project-path",
            method="POST",
            token=token,
            origin=server.origin,
            body={},
        )
        require(paste_status == 200, "Explicit clipboard route failed.")
        require(json.loads(paste_body)["project_root"] == str(project_root), "Clipboard path normalization failed.")

        progress_status, progress_headers, progress_body = request(
            server, "/api/progress", token=token
        )
        require(progress_status == 200, "Authenticated progress route failed.")
        progress = json.loads(progress_body)
        require(progress["status"] == "completed", "Initial inspection progress is incomplete.")
        require(progress["kind"] == "initial", "Initial inspection kind was lost.")
        require(progress["stage"] == "report", "Initial progress did not reach report.")
        require(progress["stage_count"] == 5, "Inspection stage contract changed.")
        require(len(progress["recent"]) <= 8, "Progress history exceeded its bound.")
        require("percent" not in progress, "Progress exposed a synthetic percentage.")
        require(
            progress_headers.get("Cache-Control") == "no-store",
            "Progress caching is not disabled.",
        )

        missing_origin, _, _ = request(
            server, "/api/rescan", method="POST", token=token, body={}
        )
        require(missing_origin == 403, "POST route accepted a missing Origin.")
        rescan_result: list[tuple[int, dict[str, str], bytes]] = []
        emitted_progress: list[tuple[str, str, str]] = []
        original_progress_emit = service._progress.emit

        def capture_progress(stage: str, source: str, event: str) -> None:
            emitted_progress.append((stage, source, event))
            original_progress_emit(stage, source, event)

        service._progress.emit = capture_progress  # type: ignore[method-assign]

        def run_rescan() -> None:
            rescan_result.append(
                request(
                    server,
                    "/api/rescan",
                    method="POST",
                    token=token,
                    origin=server.origin,
                    body={},
                )
            )

        rescan_worker = threading.Thread(target=run_rescan, daemon=True)
        rescan_worker.start()
        observed_progress: list[dict[str, object]] = []
        while rescan_worker.is_alive():
            live_status, _, live_body = request(server, "/api/progress", token=token)
            require(live_status == 200, "Progress route failed during re-scan.")
            observed_progress.append(json.loads(live_body))
            time.sleep(0.01)
        rescan_worker.join(timeout=5)
        service._progress.emit = original_progress_emit  # type: ignore[method-assign]
        require(not rescan_worker.is_alive(), "Re-scan worker did not finish.")
        require(len(rescan_result) == 1, "Re-scan response was not captured.")
        rescanned, _, rescan_body = rescan_result[0]
        require(rescanned == 200, "Authenticated re-scan failed.")
        require(
            json.loads(rescan_body)["integrity"]["control_files_unchanged_during_inspection"],
            "Re-scan observed control-file mutation.",
        )
        require(
            any(
                progress["status"] == "running"
                and isinstance(progress["current_source"], str)
                and bool(progress["current_source"])
                for progress in observed_progress
            ),
            "Live progress endpoint never exposed a running source.",
        )
        require(
            any(
                stage == "doctor" and source == "scripts/sdad.py"
                for stage, source, _event in emitted_progress
            ),
            "Inspection progress did not emit the actual Doctor source.",
        )
        completed_status, _, completed_body = request(
            server, "/api/progress", token=token
        )
        require(completed_status == 200, "Completed progress route failed.")
        completed = json.loads(completed_body)
        require(completed["status"] == "completed", "Re-scan progress is incomplete.")
        require(completed["kind"] == "rescan", "Re-scan progress kind was lost.")
        require(completed["stage"] == "report", "Re-scan did not reach report.")
        require(
            completed["current_source"] == "Inspector snapshot (memory)",
            "Completed progress lost its actual in-memory report source.",
        )

        unknown, _, _ = request(server, "/api/run", token=token)
        require(unknown == 404, "An undeclared API route is reachable.")
        traversal, _, _ = request(server, "/%2e%2e/pyproject.toml")
        require(traversal == 404, "Static path traversal was not rejected.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        app_data.cleanup()

    after = project_fingerprint(project_root)
    require(before == after, "Browser contract validation modified a project file.")
    project_data.cleanup()
    print(
        "Browser contract OK: loopback-only, token/Host/Origin enforced, "
        "CSP/no-CORS present, fixed live document/activity/recent/Rule 5 routes, "
        f"bounded real progress, {rule5_observation}, project writes 0."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
