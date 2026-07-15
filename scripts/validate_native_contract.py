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
        "scripts/smoke_release_archive.py",
        "retention-days: 3",
        "libegl1",
    ):
        if portable_contract not in workflow:
            raise AssertionError(f"missing portable CI contract: {portable_contract}")

    spec = (ROOT / "packaging" / "sdad-inspector.spec").read_text(encoding="utf-8")
    for resource in ("web/dist", "sdad-engine", "analysis.binaries", "analysis.datas", '"webview"'):
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
