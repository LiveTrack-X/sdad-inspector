from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdad_inspector.desktop import resource_root
from sdad_inspector.engine import probe_engine
from sdad_inspector.packaging import stage_release_engine


def _tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    ignored = {".git", ".runtime", ".venv", "build", "node_modules", "__pycache__"}
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts) or not path.is_file():
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate native preview contracts.")
    parser.add_argument("--sdad-checkout", default=".runtime/sdad-v3.2.2")
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    checkout = (ROOT / arguments.sdad_checkout).resolve(strict=True)
    before = _tree_fingerprint(ROOT)

    workflow = (ROOT / ".github" / "workflows" / "cross-platform.yml").read_text(
        encoding="utf-8"
    )
    for runner in ("windows-latest", "macos-latest", "ubuntu-latest"):
        if runner not in workflow:
            raise AssertionError(f"missing CI runner: {runner}")
    forbidden = (
        "gh release",
        "twine upload",
        "codesign",
        "signtool",
        "notarize",
    )
    for pattern in forbidden:
        if pattern.casefold() in workflow.casefold():
            raise AssertionError(f"protected action appears in CI: {pattern}")
    for portable_contract in (
        "portable-smoke",
        "actions/upload-artifact@v7",
        "actions/download-artifact@v8",
        "python scripts/validate_browser_contract.py --sdad-checkout .ci/sdad-v3.2.2",
        "python scripts/validate_static_report.py --sdad-checkout .ci/sdad-v3.2.2",
        "scripts/smoke_release_archive.py",
        "scripts/validate_windows_branding.py",
        "retention-days: 3",
        "libegl1",
    ):
        if portable_contract not in workflow:
            raise AssertionError(f"missing portable CI contract: {portable_contract}")

    spec = (ROOT / "packaging" / "sdad-inspector.spec").read_text(encoding="utf-8")
    for resource in ("web/dist", "sdad-engine", "analysis.binaries", "analysis.datas", '"webview"', "sdad-inspector.ico", "sdad-inspector.icns", "sdad-inspector-version.txt", "icon=ICON", "version=VERSION_INFO"):
        if resource not in spec:
            raise AssertionError(f"missing bundled resource: {resource}")
    for one_folder_construct in ("COLLECT(", "BUNDLE(", "exclude_binaries=True"):
        if one_folder_construct in spec:
            raise AssertionError(
                f"portable spec contains one-folder construct: {one_folder_construct}"
            )
    desktop_source = (ROOT / "sdad_inspector" / "desktop.py").read_text(encoding="utf-8")
    if "js_api" in desktop_source:
        raise AssertionError("desktop shell must not expose a JavaScript bridge")
    for desktop_contract in ("desktop_icon_path", "sdad-inspector-logo.png", "sdad-inspector.ico", "sdad-inspector.icns", "set_update_exit_callback", "check_product_update"):
        if desktop_contract not in desktop_source:
            raise AssertionError(f"missing desktop update/brand contract: {desktop_contract}")

    protocol_source = (ROOT / "sdad_inspector" / "protocols.py").read_text(encoding="utf-8")
    snapshot_source = (ROOT / "sdad_inspector" / "snapshot.py").read_text(encoding="utf-8")
    for protocol_contract in (
        "class ProtocolAdapter(ABC)",
        'DEFAULT_PROTOCOL_ADAPTER_ID = "official-sdad-3"',
        "resolve_protocol_adapter",
        "register_protocol_adapter",
        "adapter.validate_engine(engine)",
        'SNAPSHOT_SCHEMA_VERSION = 2',
    ):
        if protocol_contract not in protocol_source and protocol_contract not in snapshot_source:
            raise AssertionError(f"missing Inspector/SDAD adapter contract: {protocol_contract}")

    native_entry = (ROOT / "sdad_inspector" / "native_entry.py").read_text(encoding="utf-8")
    updater = (ROOT / "sdad_inspector" / "updater.py").read_text(encoding="utf-8")
    for update_contract in (
        "INTERNAL_UPDATE_FLAG",
        "apply_update_plan",
        'release.get("immutable") is not True',
        "asset_sha256",
        "extract_single_executable",
        "PARENT_EXIT_TIMEOUT_SECONDS",
        "refresh_windows_icon_cache",
    ):
        if update_contract not in native_entry and update_contract not in updater:
            raise AssertionError(f"missing bounded product-update contract: {update_contract}")
    brand_assets = (
        ROOT / "web" / "public" / "sdad-inspector-logo.png",
        ROOT / "web" / "public" / "sdad-inspector-banner.png",
        ROOT / "packaging" / "sdad-inspector.ico",
        ROOT / "packaging" / "sdad-inspector.icns",
    )
    for asset in brand_assets:
        if not asset.is_file() or asset.stat().st_size < 1024:
            raise AssertionError(f"missing or empty product brand asset: {asset.relative_to(ROOT)}")
    version_info = ROOT / "packaging" / "sdad-inspector-version.txt"
    if not version_info.is_file() or "ProductVersion', '0.0.1'" not in version_info.read_text(encoding="utf-8"):
        raise AssertionError("missing Windows 0.0.1 version resource")

    simulated = ROOT / "bundle" / "_MEI12345" / "sdad_inspector" / "desktop.py"
    if resource_root(simulated) != ROOT / "bundle" / "_MEI12345":
        raise AssertionError("frozen resource root is not deterministic")

    with tempfile.TemporaryDirectory(prefix="sdad-inspector-native-") as temporary:
        staged = stage_release_engine(checkout, Path(temporary) / "sdad-engine")
        reprobe = probe_engine(staged.path)
        if reprobe.revision != staged.engine.revision or not reprobe.clean:
            raise AssertionError("staged release engine failed reauthentication")

    after = _tree_fingerprint(ROOT)
    if before != after:
        raise AssertionError("native contract validation changed the project tree")
    print(
        json.dumps(
            {
                "native_contract": "passed",
                "project_writes": 0,
                "engine_release": reprobe.release_tag,
                "engine_revision": reprobe.revision,
                "engine_tree_sha256": staged.tree_sha256,
                "ci_matrix": ["windows-latest", "macos-latest", "ubuntu-latest"],
                "package_mode": "unsigned-one-file-portable",
                "product_update_mode": "immutable-release verified self-replace",
                "brand_assets": [asset.relative_to(ROOT).as_posix() for asset in brand_assets],
                "platform_execution_claim": "not established by this validator",
                "ephemeral_ci_artifacts": "3-day retention",
                "public_release_actions": "absent",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
