from __future__ import annotations

import importlib
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

from .engine import EngineInfo
from .dialogs import read_clipboard_text
from .errors import InspectorError
from .server import InspectorHTTPServer, InspectorService, create_server


def resource_root(module_file: str | Path | None = None) -> Path:
    """Return the source root or PyInstaller's extracted one-file resource root."""

    location = Path(module_file or __file__).resolve(strict=False)
    return location.parents[1]


def resolve_resources(
    *,
    sdad_checkout: str | Path | None = None,
    web_root: str | Path | None = None,
    module_file: str | Path | None = None,
) -> tuple[Path, Path]:
    root = resource_root(module_file)
    web = Path(web_root).expanduser() if web_root is not None else root / "web" / "dist"
    engine = (
        Path(sdad_checkout).expanduser()
        if sdad_checkout is not None
        else root / "sdad-engine"
    )
    if sdad_checkout is None and not engine.is_dir():
        raise InspectorError(
            "Source mode requires an explicit --sdad-checkout; the bundled release engine was not found.",
            details={"expected": str(engine)},
        )
    return web, engine


def load_webview() -> ModuleType:
    try:
        return importlib.import_module("webview")
    except (ImportError, OSError) as exc:
        raise InspectorError(
            "The optional desktop runtime is unavailable. Install the desktop dependency for this platform."
        ) from exc


class DesktopApplication:
    def __init__(
        self,
        project_root: str | Path,
        sdad_checkout: str | Path,
        web_root: str | Path,
        *,
        port: int = 0,
        engine_info: EngineInfo | None = None,
    ) -> None:
        service = InspectorService(
            project_root,
            sdad_checkout,
            engine_info=engine_info,
        )
        self.service = service
        self.server: InspectorHTTPServer = create_server(service, web_root, port=port)
        self._server_thread: threading.Thread | None = None
        self._stop_lock = threading.Lock()
        self._stopped = False

    def _serve(self) -> None:
        self.server.serve_forever(poll_interval=0.2)

    def _start_server(self) -> None:
        if self._server_thread is not None:
            return
        thread = threading.Thread(
            target=self._serve,
            name="sdad-inspector-loopback",
            daemon=True,
        )
        self._server_thread = thread
        thread.start()

    def stop(self) -> None:
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True
        thread = self._server_thread
        if thread is not None and thread.is_alive():
            self.server.shutdown()
        self.server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)

    def run(
        self,
        *,
        hidden: bool = False,
        smoke_seconds: float | None = None,
        webview_module: ModuleType | Any | None = None,
    ) -> int:
        if smoke_seconds is not None and smoke_seconds <= 0:
            raise InspectorError("--smoke-seconds must be greater than zero.")
        webview = webview_module or load_webview()
        self._start_server()
        window = webview.create_window(
            "SDAD Inspector",
            self.server.origin + "/",
            width=1440,
            height=960,
            min_size=(720, 600),
            hidden=hidden,
            background_color="#ffffff",
            text_select=True,
            zoomable=False,
        )

        def pick_project(initial: str | None) -> str | None:
            selected = window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=initial or str(self.service.project_root),
                allow_multiple=False,
            )
            if isinstance(selected, (list, tuple)):
                return str(selected[0]) if selected else None
            return str(selected) if selected else None

        def pick_rule_export(suggested_filename: str) -> str | None:
            file_dialog = getattr(webview, "FileDialog", None)
            dialog_kind = getattr(file_dialog, "SAVE", getattr(webview, "SAVE_DIALOG", 30))
            selected = window.create_file_dialog(
                dialog_kind,
                save_filename=suggested_filename,
                file_types=("Markdown files (*.md)",),
            )
            if isinstance(selected, (list, tuple)):
                return str(selected[0]) if selected else None
            return str(selected) if selected else None

        self.service.set_project_picker(pick_project)
        self.service.set_clipboard_reader(read_clipboard_text)
        self.service.set_rule_export_picker(pick_rule_export)

        def close_server(*_: object) -> None:
            self.stop()

        window.events.closed += close_server
        timer: threading.Timer | None = None
        if smoke_seconds is not None:

            def schedule_smoke_close(*_: object) -> None:
                nonlocal timer
                timer = threading.Timer(smoke_seconds, window.destroy)
                timer.daemon = True
                timer.start()

            window.events.loaded += schedule_smoke_close
        try:
            webview.start(private_mode=False)
        finally:
            if timer is not None:
                timer.cancel()
            self.stop()
        return 0


def run_desktop(
    project_root: str | Path,
    sdad_checkout: str | Path | None = None,
    web_root: str | Path | None = None,
    *,
    hidden: bool = False,
    smoke_seconds: float | None = None,
    port: int = 0,
) -> int:
    resolved_web, resolved_engine = resolve_resources(
        sdad_checkout=sdad_checkout,
        web_root=web_root,
    )
    application = DesktopApplication(
        project_root,
        resolved_engine,
        resolved_web,
        port=port,
    )
    return application.run(hidden=hidden, smoke_seconds=smoke_seconds)
