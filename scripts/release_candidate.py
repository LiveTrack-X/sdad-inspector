"""Bind verified CI archives to one source commit, version and trusted run.

Local create/verify are offline. select/remote-check only inspect GitHub; they
never create or move a tag, change a Release, build, or approve publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

try:
    from scripts.release_metadata import VERSION, TAG
except ModuleNotFoundError:
    from release_metadata import VERSION, TAG

MANIFEST = "candidate-manifest.json"
WORKFLOW = ".github/workflows/cross-platform.yml"


def archive_names(version: str) -> set[str]:
    return {f"SDAD-Inspector-{version}-{suffix}" for suffix in (
        "windows-x64.zip", "macos-arm64.tar.gz", "linux-x64.tar.gz")}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def identity(commit: str, version: str, repository: str, run_id: str, attempt: str) -> dict:
    if (not re.fullmatch(r"[0-9a-f]{40}", commit)
            or not re.fullmatch(r"\d+\.\d+\.\d+", version)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or not re.fullmatch(r"[1-9]\d*", run_id)
            or not re.fullmatch(r"[1-9]\d*", attempt)):
        raise ValueError("Invalid candidate identity")
    return {"schema_version": 1, "commit": commit, "version": version,
            "repository": repository, "run_id": run_id, "run_attempt": attempt,
            "workflow": WORKFLOW}


def archive_records(directory: Path, version: str) -> list[dict]:
    expected = archive_names(version)
    entries = list(directory.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError("Candidate must contain regular files only")
    if {p.name for p in entries} - {MANIFEST, "SHA256SUMS"} != expected:
        raise ValueError("Candidate archive set does not match version/platform contract")
    return [{"name": name, "bytes": (directory / name).stat().st_size,
             "sha256": digest(directory / name)} for name in sorted(expected)]


def create(directory: Path, expected: dict) -> dict:
    manifest = {**expected, "archives": archive_records(directory, expected["version"])}
    if (directory / MANIFEST).exists():
        raise ValueError("Candidate manifest already exists; never replace an existing identity")
    (directory / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate candidate manifest key")
        result[key] = value
    return result


def verify(directory: Path, expected: dict, tag: str) -> dict:
    if tag != "v" + expected["version"]:
        raise ValueError("Tag and current source version differ")
    path = directory / MANIFEST
    if path.is_symlink() or path.stat().st_size > 32 * 1024:
        raise ValueError("Invalid candidate manifest file")
    manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique)
    if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
            or set(manifest) != set(expected) | {"archives"}):
        raise ValueError("Unsupported candidate manifest structure")
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError("Candidate commit/version/repository/run identity mismatch")
    if manifest["archives"] != archive_records(directory, expected["version"]):
        raise ValueError("Candidate artifact hash/size manifest mismatch")
    return manifest


def validate_run(run: dict, repository: str, commit: str) -> None:
    if (run.get("conclusion") != "success" or run.get("status") != "completed"
            or run.get("head_sha") != commit or run.get("head_branch") != "main"
            or run.get("event") != "push" or run.get("path") != WORKFLOW
            or (run.get("repository") or {}).get("full_name") != repository
            or (run.get("head_repository") or {}).get("full_name") != repository):
        raise ValueError("Candidate must be a successful same-commit main push in this repository")


def api(repository: str, suffix: str):
    result = subprocess.run(["gh", "api", f"repos/{repository}/{suffix}"],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def check_remote_tag(repository: str, tag: str, commit: str) -> None:
    if tag != TAG:
        raise ValueError("Release tag must equal the source version")
    obj = api(repository, f"git/ref/tags/{tag}")["object"]
    for _ in range(4):
        if obj.get("type") == "commit":
            if obj.get("sha") != commit:
                raise ValueError("Remote tag moved or differs from the checked-out commit")
            return
        if obj.get("type") != "tag" or not re.fullmatch(r"[0-9a-f]{40}", obj.get("sha", "")):
            break
        obj = api(repository, "git/tags/" + obj["sha"])["object"]
    raise ValueError("Release tag does not resolve to the expected commit")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify", "select", "remote-check"))
    parser.add_argument("--directory", type=Path, default=Path("release-artifacts"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--attempt", default="1")
    parser.add_argument("--tag", default=TAG)
    args = parser.parse_args()
    # Validate inputs before building any API path or interpreting a manifest.
    identity(args.commit, VERSION, args.repository, args.run_id or "1", args.attempt)
    if args.action in {"select", "remote-check"}:
        check_remote_tag(args.repository, args.tag, args.commit)
        if args.action == "remote-check":
            return 0
        if args.run_id:
            run = api(args.repository, f"actions/runs/{args.run_id}")
        else:
            candidates = api(args.repository,
                f"actions/workflows/cross-platform.yml/runs?head_sha={args.commit}&branch=main&event=push&status=success&per_page=100")["workflow_runs"]
            if not candidates:
                raise ValueError("No successful candidate for this exact commit; do not move the tag or rebuild under it")
            run = candidates[0]
        validate_run(run, args.repository, args.commit)
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"run_id={int(run['id'])}\nattempt={int(run['run_attempt'])}\ncommit={args.commit}\n")
        return 0
    expected = identity(args.commit, VERSION, args.repository, args.run_id, args.attempt)
    if args.action == "create":
        create(args.directory, expected)
    else:
        verify(args.directory, expected, args.tag)
    print(f"Candidate {args.action} passed: {args.commit}, {VERSION}, three archive identities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
