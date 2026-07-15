from __future__ import annotations

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
ENGINE = Path(os.environ["SDAD_INSPECTOR_ENGINE_DIR"]).resolve(strict=True)
WEB = (ROOT / "web" / "dist").resolve(strict=True)

webview_datas, webview_binaries, webview_hiddenimports = collect_all("webview")
datas = webview_datas + [
    (str(WEB), "web/dist"),
    (str(ENGINE), "sdad-engine"),
]

analysis = Analysis(
    [str(ROOT / "sdad_inspector" / "native_entry.py")],
    pathex=[str(ROOT)],
    binaries=webview_binaries,
    datas=datas,
    hiddenimports=webview_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="SDAD-Inspector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SDAD-Inspector",
)

if sys.platform == "darwin":
    application = BUNDLE(
        collection,
        name="SDAD Inspector.app",
        icon=None,
        bundle_identifier="io.livetrackx.sdad-inspector.preview",
    )
