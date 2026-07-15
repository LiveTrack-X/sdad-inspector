from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import sdad_inspector.engine as engine_module
from sdad_inspector.desktop import DesktopApplication, desktop_icon_path, resolve_resources, resource_root
from sdad_inspector.engine import _engine_argv
from sdad_inspector.errors import EngineError, InspectorError

from test_core import WorkspaceCase


class FakeEvent:
    def __init__(self) -> None:
        self.handlers: list[object] = []

    def __iadd__(self, handler: object) -> "FakeEvent":
        self.handlers.append(handler)
        return self

    def emit(self) -> None:
        for handler in tuple(self.handlers):
            handler()  # type: ignore[operator]


class FakeEvents:
    def __init__(self) -> None:
        self.closed = FakeEvent()
        self.loaded = FakeEvent()


class FakeWindow:
    def __init__(self) -> None:
        self.events = FakeEvents()
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True
        self.events.closed.emit()


class FakeWebview:
    def __init__(self, *, emit_loaded: bool = False) -> None:
        self.window = FakeWindow()
        self.emit_loaded = emit_loaded
        self.create_args: tuple[object, ...] = ()
        self.create_kwargs: dict[str, object] = {}
        self.start_kwargs: dict[str, object] = {}

    def create_window(self, *args: object, **kwargs: object) -> FakeWindow:
        self.create_args = args
        self.create_kwargs = kwargs
        return self.window

    def start(self, **kwargs: object) -> None:
        self.start_kwargs = kwargs
        if self.emit_loaded:
            self.window.events.loaded.emit()
        else:
            self.window.events.closed.emit()


class ImmediateTimer:
    def __init__(self, _seconds: float, callback: object) -> None:
        self.callback = callback
        self.daemon = False

    def start(self) -> None:
        self.callback()  # type: ignore[operator]

    def cancel(self) -> None:
        return


class DesktopResourceTests(WorkspaceCase):
    def setUp(self) -> None:
        super().setUp()
        self.web = self.root / "web" / "dist"
        self.web.mkdir(parents=True)
        (self.web / "index.html").write_text(
            '<meta name="sdad-session" content="__SDAD_SESSION_TOKEN__">',
            encoding="utf-8",
        )

    def application(self) -> DesktopApplication:
        return DesktopApplication(
            self.project,
            self.engine,
            self.web,
            engine_info=self.engine_info,
        )

    def test_resource_root_is_stable_for_source_and_frozen_layouts(self) -> None:
        source_file = self.root / "repo" / "sdad_inspector" / "desktop.py"
        frozen_file = self.root / "bundle" / "_MEI12345" / "sdad_inspector" / "desktop.py"
        self.assertEqual(resource_root(source_file), (self.root / "repo").resolve())
        self.assertEqual(
            resource_root(frozen_file), (self.root / "bundle" / "_MEI12345").resolve()
        )

    def test_source_mode_requires_an_explicit_release_engine(self) -> None:
        module_file = self.root / "repo" / "sdad_inspector" / "desktop.py"
        with self.assertRaises(InspectorError):
            resolve_resources(module_file=module_file)
        web, engine = resolve_resources(
            sdad_checkout=self.engine,
            web_root=self.web,
            module_file=module_file,
        )
        self.assertEqual(web, self.web)
        self.assertEqual(engine, self.engine)

    def test_window_icon_matches_each_platform_asset(self) -> None:
        module_file = self.root / "repo" / "sdad_inspector" / "desktop.py"
        windows_icon = self.root / "repo" / "packaging" / "sdad-inspector.ico"
        macos_icon = self.root / "repo" / "packaging" / "sdad-inspector.icns"
        linux_icon = self.web / "sdad-inspector-logo.png"
        windows_icon.parent.mkdir(parents=True)
        windows_icon.write_bytes(b"fixture-ico")
        macos_icon.write_bytes(b"fixture-icns")
        linux_icon.write_bytes(b"fixture-png")
        for platform, expected in (
            ("win32", windows_icon),
            ("darwin", macos_icon),
            ("linux", linux_icon),
        ):
            with self.subTest(platform=platform), patch(
                "sdad_inspector.desktop.sys.platform", platform
            ):
                actual = desktop_icon_path(self.web, module_file)
                self.assertIsNotNone(actual)
                self.assertEqual(
                    actual.resolve(strict=True),  # type: ignore[union-attr]
                    expected.resolve(strict=True),
                )

    def test_frozen_runtime_routes_only_the_bundled_engine_to_internal_runner(self) -> None:
        internal = self.root / "bundle" / "_internal"
        module_file = internal / "sdad_inspector" / "engine.py"
        script = internal / "sdad-engine" / "scripts" / "sdad.py"
        script.parent.mkdir(parents=True)
        script.write_text("raise SystemExit(0)\n", encoding="utf-8")
        external = self.root / "external" / "scripts" / "sdad.py"
        external.parent.mkdir(parents=True)
        external.write_text("raise SystemExit(0)\n", encoding="utf-8")
        with (
            patch.object(engine_module, "__file__", str(module_file)),
            patch.object(engine_module.sys, "frozen", True, create=True),
            patch.object(engine_module.sys, "executable", "SDAD-Inspector.exe"),
        ):
            self.assertEqual(
                _engine_argv(script, "--version"),
                ["SDAD-Inspector.exe", "--sdad-internal-engine", "--version"],
            )
            with self.assertRaises(EngineError):
                _engine_argv(external, "--version")

    def test_window_uses_loopback_without_a_javascript_bridge_and_stops(self) -> None:
        application = self.application()
        webview = FakeWebview()
        icon = self.root / "app-icon"
        icon.write_bytes(b"fixture-icon")
        with patch("sdad_inspector.desktop.desktop_icon_path", return_value=icon):
            result = application.run(webview_module=webview)
        self.assertEqual(result, 0)
        self.assertEqual(webview.create_args[0], "SDAD Inspector")
        self.assertTrue(str(webview.create_args[1]).startswith("http://127.0.0.1:"))
        self.assertNotIn("js_api", webview.create_kwargs)
        self.assertFalse(webview.start_kwargs["private_mode"])
        self.assertEqual(Path(str(webview.start_kwargs["icon"])), icon)
        self.assertFalse(application._server_thread.is_alive())  # type: ignore[union-attr]

    def test_bounded_hidden_smoke_destroys_the_window(self) -> None:
        application = self.application()
        webview = FakeWebview(emit_loaded=True)
        with patch("sdad_inspector.desktop.threading.Timer", ImmediateTimer):
            result = application.run(
                hidden=True,
                smoke_seconds=0.1,
                webview_module=webview,
            )
        self.assertEqual(result, 0)
        self.assertTrue(webview.window.destroyed)
        self.assertTrue(webview.create_kwargs["hidden"])

    def test_stop_is_idempotent_before_and_after_server_start(self) -> None:
        application = self.application()
        application._start_server()
        application.stop()
        application.stop()
        self.assertFalse(application._server_thread.is_alive())  # type: ignore[union-attr]


if __name__ == "__main__":
    import unittest

    unittest.main()
