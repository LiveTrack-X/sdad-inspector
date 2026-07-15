from __future__ import annotations

import hmac
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlsplit

from .activity import load_development_activity
from .dialogs import normalize_clipboard_path, read_clipboard_text, select_markdown_export_path, select_project_directory
from .engine import EngineInfo, probe_engine
from .errors import InspectorError
from .paths import canonical_directory, safe_project_path
from .preferences import PREFERENCES_SCHEMA_VERSION, RecentProjectsStore
from .progress import InspectionProgress
from .rule5 import build_rule5_proposal, extract_rule5_candidates, write_rule5_export
from .snapshot import inspect_project
from .state import load_live_documents
from .updater import ProductUpdateManager

MAX_REQUEST_BYTES = 64 * 1024


class InspectorService:
    def __init__(
        self,
        project_root: str | Path,
        sdad_checkout: str | Path,
        *,
        timeout: float = 30,
        engine_info: EngineInfo | None = None,
        project_picker: Callable[[str | None], str | None] | None = None,
        clipboard_reader: Callable[[], str] | None = None,
        preferences_store: RecentProjectsStore | None = None,
        rule_export_picker: Callable[[str], str | None] | None = None,
        update_manager: ProductUpdateManager | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._operation_lock = threading.Lock()
        self._progress = InspectionProgress()
        self.timeout = timeout
        self.sdad_checkout = canonical_directory(sdad_checkout, label="SDAD checkout")
        self.engine = engine_info or probe_engine(self.sdad_checkout)
        self._project_picker = project_picker
        self._clipboard_reader = clipboard_reader
        self._recent_projects = preferences_store or RecentProjectsStore()
        self._rule_export_picker = rule_export_picker
        self._updates = update_manager or ProductUpdateManager()
        self._update_exit_callback: Callable[[], None] | None = None
        root = canonical_directory(project_root, label="Project root")
        snapshot = self._inspect(root, kind="initial")
        self._project_root = root
        self._snapshot = snapshot

    def _inspect(self, root: Path, *, kind: str) -> dict[str, Any]:
        self._progress.start(kind)
        try:
            snapshot = inspect_project(
                root,
                self.sdad_checkout,
                timeout=self.timeout,
                _engine_info=self.engine,
                progress_callback=self._progress.emit,
            )
        except Exception as exc:
            self._progress.fail(type(exc).__name__)
            raise
        self._progress.complete()
        return snapshot

    @property
    def project_root(self) -> Path:
        with self._lock:
            return self._project_root

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot

    def progress(self) -> dict[str, Any]:
        return self._progress.snapshot()

    def set_project_picker(
        self, picker: Callable[[str | None], str | None] | None
    ) -> None:
        self._project_picker = picker

    def set_clipboard_reader(self, reader: Callable[[], str] | None) -> None:
        self._clipboard_reader = reader

    def set_rule_export_picker(
        self, picker: Callable[[str], str | None] | None
    ) -> None:
        self._rule_export_picker = picker

    def set_update_exit_callback(self, callback: Callable[[], None] | None) -> None:
        self._update_exit_callback = callback

    def update_status(self) -> dict[str, Any]:
        return self._updates.status()

    def check_product_update(self, *, force: bool = False) -> dict[str, Any]:
        return self._updates.start_background_check(force=force)

    def apply_product_update(self) -> dict[str, Any]:
        callback = self._update_exit_callback
        if callback is None:
            raise InspectorError("The desktop restart bridge is unavailable.")
        status = self._updates.launch_apply(project_root=self.project_root)
        timer = threading.Timer(0.35, callback)
        timer.daemon = True
        timer.start()
        return status

    def documents(self) -> dict[str, Any]:
        with self._lock:
            root = self._project_root
        return load_live_documents(root)

    def activity(self) -> dict[str, Any]:
        with self._lock:
            root = self._project_root
        return load_development_activity(root)

    def recent_projects(self) -> dict[str, Any]:
        return {
            "schema_version": PREFERENCES_SCHEMA_VERSION,
            "recent_projects": self._recent_projects.load(),
        }

    def clear_recent_projects(self) -> dict[str, Any]:
        self._recent_projects.clear()
        return {
            "schema_version": PREFERENCES_SCHEMA_VERSION,
            "recent_projects": [],
        }

    def rule5_candidates(self) -> dict[str, Any]:
        with self._lock:
            root = self._project_root
        return extract_rule5_candidates(root)

    def rule5_preview(self, payload: dict[str, Any]) -> dict[str, str]:
        current = self.rule5_candidates()
        if payload.get("source_sha256") != current["source_sha256"]:
            raise InspectorError("The Rule 5 finding source changed. Extract it again.")
        finding_id = payload.get("finding_id")
        if finding_id not in {candidate["finding_id"] for candidate in current["candidates"]}:
            raise InspectorError("The Rule 5 finding is no longer active.")
        return build_rule5_proposal(payload)

    def export_rule5(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("confirmed") is not True:
            raise InspectorError("Review and explicitly confirm the Rule 5 preview before saving.")
        preview_sha256 = payload.get("preview_sha256")
        if not isinstance(preview_sha256, str):
            raise InspectorError("The Rule 5 preview identity is required.")
        with self._operation_lock:
            preview = self.rule5_preview(payload)
            if not hmac.compare_digest(preview["sha256"], preview_sha256):
                raise InspectorError("The Rule 5 preview changed. Review it again before saving.")
            picker = self._rule_export_picker
            if picker is None:
                raise InspectorError("The system Save As dialog is unavailable.")
            selected = picker(preview["suggested_filename"])
            if not selected:
                return {"saved": False, "cancelled": True, "path": None, **preview}
            destination = write_rule5_export(
                selected,
                preview["markdown"],
                forbidden_root=self.project_root,
            )
            return {
                "saved": True,
                "cancelled": False,
                "path": str(destination),
                **preview,
            }

    def pick_project(self, initial_path: str | None = None) -> dict[str, Any]:
        picker = self._project_picker
        if picker is None:
            raise InspectorError("The system folder picker is unavailable.")
        selected = picker(initial_path or str(self.project_root))
        return {
            "selected": bool(selected),
            "project_root": str(selected) if selected else None,
        }

    def paste_project_path(self) -> dict[str, Any]:
        reader = self._clipboard_reader
        if reader is None:
            raise InspectorError("Clipboard access is unavailable.")
        return {"project_root": normalize_clipboard_path(reader())}

    def rescan(self) -> dict[str, Any]:
        with self._operation_lock:
            with self._lock:
                root = self._project_root
            snapshot = self._inspect(root, kind="rescan")
            with self._lock:
                self._snapshot = snapshot
            return snapshot

    def open_project(self, project_root: str) -> dict[str, Any]:
        candidate = canonical_directory(project_root, label="Project root")
        with self._operation_lock:
            with self._lock:
                previous = self._project_root
            snapshot = self._inspect(candidate, kind="open_project")
            with self._lock:
                self._project_root = candidate
                self._snapshot = snapshot
            try:
                self._recent_projects.remember(
                    ((previous, previous.name), (candidate, candidate.name))
                )
            except OSError:
                # Preference persistence must never block an otherwise valid
                # read-only project switch.
                pass
            return snapshot

    def reveal(self, relative_path: str) -> Path:
        with self._lock:
            root = self._project_root
        if relative_path in {"", "."}:
            target = root
        else:
            target = safe_project_path(
                root,
                relative_path,
                purpose="revealed file",
                must_exist=True,
                regular_file=True,
            )
        if sys.platform == "win32":
            if target.is_dir():
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["explorer.exe", f"/select,{target}"], shell=False)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)], shell=False)
        else:
            location = target if target.is_dir() else target.parent
            subprocess.Popen(["xdg-open", str(location)], shell=False)
        return target


class InspectorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        address: tuple[str, int],
        service: InspectorService,
        static_root: Path,
        session_token: str,
    ) -> None:
        self.service = service
        self.static_root = static_root
        self.session_token = session_token
        super().__init__(address, InspectorRequestHandler)

    @property
    def origin(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def authority(self) -> str:
        host, port = self.server_address[:2]
        return f"{host}:{port}"


class InspectorRequestHandler(BaseHTTPRequestHandler):
    server: InspectorHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _security_headers(self, *, api: bool = False) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        )
        self.send_header("Cache-Control", "no-store" if api else "no-cache")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._security_headers(api=True)
        self.end_headers()
        self.wfile.write(data)

    def _valid_host(self) -> bool:
        return hmac.compare_digest(self.headers.get("Host", ""), self.server.authority)

    def _valid_origin(self, *, required: bool) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return not required
        return hmac.compare_digest(origin, self.server.origin)

    def _valid_token(self) -> bool:
        supplied = self.headers.get("X-SDAD-Session", "")
        return bool(supplied) and hmac.compare_digest(supplied, self.server.session_token)

    def _authorize_api(self, *, mutation: bool) -> bool:
        if not self._valid_host():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": {"code": "invalid_host"}})
            return False
        if not self._valid_origin(required=mutation):
            self._send_json(HTTPStatus.FORBIDDEN, {"error": {"code": "invalid_origin"}})
            return False
        if not self._valid_token():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": {"code": "invalid_session"}})
            return False
        return True

    def _read_json(self) -> dict[str, Any] | None:
        if self.headers.get_content_type() != "application/json":
            self._send_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {"error": {"code": "json_required"}},
            )
            return None
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": {"code": "request_too_large"}},
            )
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": {"code": "invalid_json"}})
            return None
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": {"code": "object_required"}})
            return None
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path.startswith("/api/"):
            if not self._authorize_api(mutation=False):
                return
            if path == "/api/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "read_only": True,
                        "snapshot_schema_version": 1,
                    },
                )
                return
            if path == "/api/snapshot":
                self._send_json(HTTPStatus.OK, self.server.service.snapshot())
                return
            if path == "/api/progress":
                self._send_json(HTTPStatus.OK, self.server.service.progress())
                return
            try:
                if path == "/api/documents":
                    self._send_json(HTTPStatus.OK, self.server.service.documents())
                    return
                if path == "/api/activity":
                    self._send_json(HTTPStatus.OK, self.server.service.activity())
                    return
                if path == "/api/recent-projects":
                    self._send_json(HTTPStatus.OK, self.server.service.recent_projects())
                    return
                if path == "/api/rule5-candidates":
                    self._send_json(HTTPStatus.OK, self.server.service.rule5_candidates())
                    return
                if path == "/api/update":
                    self._send_json(HTTPStatus.OK, self.server.service.update_status())
                    return
            except InspectorError as exc:
                self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, exc.to_payload())
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if not self._authorize_api(mutation=True):
            return
        payload = self._read_json()
        if payload is None:
            return
        try:
            if path == "/api/rescan":
                self._send_json(HTTPStatus.OK, self.server.service.rescan())
                return
            if path == "/api/project":
                project_root = payload.get("project_root")
                if not isinstance(project_root, str) or not project_root.strip():
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": "project_root_required"}},
                    )
                    return
                self._send_json(
                    HTTPStatus.OK, self.server.service.open_project(project_root)
                )
                return
            if path == "/api/project-picker":
                initial_path = payload.get("initial_path")
                if initial_path is not None and not isinstance(initial_path, str):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": "initial_path_invalid"}},
                    )
                    return
                self._send_json(
                    HTTPStatus.OK, self.server.service.pick_project(initial_path)
                )
                return
            if path == "/api/clipboard/project-path":
                self._send_json(
                    HTTPStatus.OK, self.server.service.paste_project_path()
                )
                return
            if path == "/api/recent-projects/clear":
                try:
                    result = self.server.service.clear_recent_projects()
                except OSError:
                    self._send_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        {"error": {"code": "preferences_unavailable"}},
                    )
                    return
                self._send_json(HTTPStatus.OK, result)
                return
            if path == "/api/rule5/preview":
                self._send_json(HTTPStatus.OK, self.server.service.rule5_preview(payload))
                return
            if path == "/api/rule5/export":
                self._send_json(HTTPStatus.OK, self.server.service.export_rule5(payload))
                return
            if path == "/api/update/check":
                force = payload.get("force", False)
                if not isinstance(force, bool):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": "update_force_invalid"}},
                    )
                    return
                self._send_json(
                    HTTPStatus.OK,
                    self.server.service.check_product_update(force=force),
                )
                return
            if path == "/api/update/apply":
                self._send_json(HTTPStatus.OK, self.server.service.apply_product_update())
                return
            if path == "/api/reveal":
                relative_path = payload.get("relative_path")
                if not isinstance(relative_path, str):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": {"code": "relative_path_required"}},
                    )
                    return
                target = self.server.service.reveal(relative_path)
                self._send_json(
                    HTTPStatus.OK,
                    {"revealed": True, "relative_path": relative_path, "name": target.name},
                )
                return
        except InspectorError as exc:
            self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, exc.to_payload())
            return
        except OSError:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": {"code": "reveal_unavailable"}},
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": {"code": "not_allowed"}})

    def _serve_static(self, request_path: str) -> None:
        if not self._valid_host():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": {"code": "invalid_host"}})
            return
        relative = "index.html" if request_path in {"", "/"} else unquote(request_path.lstrip("/"))
        candidate = (self.server.static_root / relative).resolve(strict=False)
        try:
            candidate.relative_to(self.server.static_root)
        except ValueError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})
            return
        if not candidate.is_file() or candidate.is_symlink():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})
            return
        try:
            data = candidate.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})
            return
        if candidate.name == "index.html":
            data = data.replace(
                b"__SDAD_SESSION_TOKEN__", self.server.session_token.encode("ascii")
            )
        content_type, _ = mimetypes.guess_type(candidate.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self._security_headers(api=False)
        self.end_headers()
        self.wfile.write(data)


def create_server(
    service: InspectorService,
    static_root: str | Path,
    *,
    port: int = 0,
    session_token: str | None = None,
) -> InspectorHTTPServer:
    root = canonical_directory(static_root, label="Web bundle")
    if not (root / "index.html").is_file():
        raise InspectorError(
            "The web bundle does not contain index.html.", details={"path": str(root)}
        )
    token = session_token or secrets.token_urlsafe(32)
    return InspectorHTTPServer(("127.0.0.1", port), service, root, token)


def serve_browser(
    project_root: str | Path,
    sdad_checkout: str | Path,
    static_root: str | Path,
    *,
    port: int = 0,
    open_browser: bool = True,
) -> int:
    service = InspectorService(
        project_root,
        sdad_checkout,
        project_picker=lambda initial: select_project_directory(initial),
        clipboard_reader=read_clipboard_text,
        rule_export_picker=select_markdown_export_path,
    )
    server = create_server(service, static_root, port=port)
    url = server.origin + "/"
    print(url, flush=True)
    if open_browser:
        webbrowser.open(url, new=1)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
