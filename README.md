# SDAD Inspector

[![Cross-platform preview checks](https://github.com/LiveTrack-X/sdad-inspector/actions/workflows/cross-platform.yml/badge.svg)](https://github.com/LiveTrack-X/sdad-inspector/actions/workflows/cross-platform.yml)

This is the public source repository. It is not a signed product release or a
cross-platform support claim; those remain separate evidence and owner gates.

SDAD Inspector is a local, read-only viewer for repositories that use the
[SDAD protocol](https://github.com/LiveTrack-X/spec-driven-ai-development).
It turns the active packet, SPEC authority, Doctor findings, validation
declarations, owner gates, and evidence provenance into one inspectable view.
The shared browser/native interface supports Korean and English, selects Korean
for a Korean primary browser locale, and keeps an explicit local language
choice across reloads. Repository-tree selections open matching central
evidence views, re-scan and project-open operations expose only observed
Inspector stages and bounded current sources, and a local light/dark choice is
preserved across reloads. Repository evidence remains in its original language.

The product does not execute a project's validation commands, edit a project,
download an engine at runtime, or expose a JavaScript-to-Python bridge. Release,
signing, publishing, and every future write/auto-fix action remain owner-gated.

## Current evidence boundary

- Headless inspection, the loopback browser app, and static sanitized reports
  are locally verified on Windows against the authenticated SDAD v3.2.2 tree.
- The optional native shell built as an unsigned Windows one-folder preview and
  completed a bounded local launch/close smoke. Its exact evidence is tracked
  separately in `docs/CROSS_PLATFORM.md`.
- On the locally verified Windows browser and exact rebuilt preview, selecting
  a folder without readable SDAD state renders the bounded Doctor diagnostic
  surface instead of a blank screen.
- The same local bundle was exercised in Korean light/dark modes at desktop and
  narrow widths; tree parents and leaves update the central workspace and right
  Inspector, and authenticated progress contains no fabricated percentage or
  inferred repository work-loop phase.
- A checked-in matrix defines Windows, macOS, and Ubuntu builds, but a platform
  is not claimed merely because it appears in configuration.

## Future engine updates and project migration

Inspector and SDAD engine versions intentionally remain independent. A future
updater can discover compatible official GitHub Releases, authenticate a
release into a versioned local cache, run compatibility checks, and select the
new engine without changing an inspected project. Project bootstrap or schema
migration is a separate flow: recommendation, complete diff preview, explicit
owner approval, transactional apply, Doctor verification, and rollback.

The current preview does not download engines or write projects. Silent project
migration remains forbidden; apply requires Full SDAD plus the
`auto-fix/write` owner gate. The proposed contract is documented in
`docs/UPDATE_AND_MIGRATION.md`.

## Developer quick start

Requirements: Python 3.10 or newer and Node.js 22 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[desktop,build]"
npm --prefix web ci
npm --prefix web run build
```

Use only a clean supported release checkout or authenticated release archive:

```powershell
.\.venv\Scripts\sdad-inspector inspect . --sdad-checkout .runtime\sdad-v3.2.2 --pretty
.\.venv\Scripts\sdad-inspector serve . --sdad-checkout .runtime\sdad-v3.2.2
.\.venv\Scripts\sdad-inspector desktop . --sdad-checkout .runtime\sdad-v3.2.2
```

Generate a self-contained report outside the inspected project:

```powershell
.\.venv\Scripts\sdad-inspector report C:\path\to\project `
  --sdad-checkout .runtime\sdad-v3.2.2 `
  --output C:\path\outside-project\sdad-report.html `
  --redact-paths --redact-evidence
```

## Native preview build

```powershell
npm --prefix web run build
.\.venv\Scripts\python scripts\build_native.py `
  --sdad-checkout .runtime\sdad-v3.2.2
.\.venv\Scripts\python scripts\smoke_native.py .
```

The build stages and reauthenticates the complete release engine before
PyInstaller receives it. Output is under `build/native/dist`; it is unsigned,
unpublished, and not an installer.

The locally verified preview is
`build/native/dist/SDAD-Inspector/SDAD-Inspector.exe`. Keep the complete sibling
`_internal` directory beside it. Run the executable with a project path or
double-click it to choose an SDAD project through the native folder picker.

## Validation

```powershell
python -m unittest discover -s tests -v
npm --prefix web run typecheck
npm --prefix web test -- --run
npm --prefix web run build
python scripts\validate_browser_contract.py
python scripts\validate_static_report.py
python scripts\validate_native_contract.py
python scripts\build_native.py --check --sdad-checkout .runtime\sdad-v3.2.2
```

See `docs/INDEX.md` for the documentation route and
`docs/CROSS_PLATFORM.md` for platform-specific runtime and evidence limits.
Language behavior and the evidence-translation boundary are documented in
`docs/LOCALIZATION.md`.
