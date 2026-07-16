from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdad_inspector.engine import RELEASE_TREE_SHA256, probe_engine
from sdad_inspector.errors import InspectorError, PackageError
from sdad_inspector.packaging import stage_release_engine


def _run(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(argv, cwd=ROOT, env=env, shell=False, check=False)
    if result.returncode != 0:
        raise PackageError(
            "A native build prerequisite failed.",
            details={"argv": argv, "exit_code": result.returncode},
        )


def _required_paths() -> dict[str, Path]:
    return {
        "web_bundle": ROOT / "web" / "dist" / "index.html",
        "spec": ROOT / "packaging" / "sdad-inspector.spec",
        "workflow": ROOT / ".github" / "workflows" / "cross-platform.yml",
        "entrypoint": ROOT / "sdad_inspector" / "native_entry.py",
    }


def require_release_python(
    *,
    implementation: str | None = None,
    version: tuple[int, int] | None = None,
    executable: str | None = None,
) -> dict[str, object]:
    implementation = implementation or sys.implementation.name
    version = version or sys.version_info[:2]
    executable = executable or sys.executable
    if implementation != "cpython" or version != (3, 12):
        raise PackageError(
            "Portable native builds require official CPython 3.12.",
            details={
                "implementation": implementation,
                "python": f"{version[0]}.{version[1]}",
                "executable": executable,
            },
        )
    return {
        "python_implementation": implementation,
        "python_version": f"{version[0]}.{version[1]}",
        "python_executable": executable,
    }


def resolve_npm_executable(
    *,
    platform_name: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> str | None:
    """Return the directly executable npm launcher for the current platform."""

    platform_name = platform_name or os.name
    command = "npm.cmd" if platform_name == "nt" else "npm"
    return which(command)


def check_prerequisites(checkout: str | Path) -> dict[str, object]:
    engine = probe_engine(checkout)
    missing = [name for name, path in _required_paths().items() if not path.is_file()]
    if missing:
        raise PackageError(
            "Native build prerequisites are missing.", details={"missing": missing}
        )
    return {
        "ready": True,
        "release_tag": engine.release_tag,
        "revision": engine.revision,
        "trust": engine.trust,
        "web_bundle": str(_required_paths()["web_bundle"]),
        "package_mode": "unsigned-one-file-portable",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an unsigned SDAD Inspector preview.")
    parser.add_argument("--sdad-checkout", required=True)
    parser.add_argument("--output-root", default="build/native")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        evidence = check_prerequisites(arguments.sdad_checkout)
        evidence.update(require_release_python())
        if arguments.check:
            print(json.dumps(evidence, ensure_ascii=False, indent=2))
            return 0

        if not arguments.skip_frontend:
            npm = resolve_npm_executable()
            if npm is None:
                raise PackageError("npm is required to build the shared frontend.")
            _run([npm, "--prefix", "web", "run", "build"])

        output_root = (ROOT / arguments.output_root).resolve(strict=False)
        version = str(evidence["release_tag"]).removeprefix("v")
        stage_name = f"sdad-engine-{version}-{RELEASE_TREE_SHA256[version][:12]}"
        stage = stage_release_engine(
            arguments.sdad_checkout,
            output_root / stage_name,
        )
        environment = os.environ.copy()
        environment["SDAD_INSPECTOR_ENGINE_DIR"] = str(stage.path)
        _run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--distpath",
                str(output_root / "dist"),
                "--workpath",
                str(output_root / "work"),
                str(ROOT / "packaging" / "sdad-inspector.spec"),
            ],
            env=environment,
        )
        evidence.update(
            {
                "engine_stage": str(stage.path),
                "engine_tree_sha256": stage.tree_sha256,
                "engine_stage_reused": stage.reused,
                "dist": str(output_root / "dist"),
            }
        )
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    except InspectorError as exc:
        print(json.dumps(exc.to_payload(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
