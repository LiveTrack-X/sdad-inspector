from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
ENGINE = Path(os.environ["SDAD_INSPECTOR_ENGINE_DIR"]).resolve(strict=True)
WEB = (ROOT / "web" / "dist").resolve(strict=True)

webview_datas, webview_binaries, webview_hiddenimports = collect_all("webview")
webview_hiddenimports = sorted({"webview", *webview_hiddenimports})
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
    analysis.binaries,
    analysis.datas,
    [],
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
