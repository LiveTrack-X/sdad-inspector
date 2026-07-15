# Open Implementation Items

Status: Active
Scope: Current implementation backlog only

## Current Priority

1. Publish the audited current source tree as public
   `LiveTrack-X/sdad-inspector` under the explicitly authorized
   `SI-012-public-source-repository` boundary.
2. Keep GitHub Releases, artifact/package distribution, signing, deployment,
   auto-fix/write, and unsupported platform claims outside this source-only
   publication.

## Active Work

- [x] [packet:SI-012-public-source-repository] Replace personal absolute paths
  and machine-specific npm cache configuration with public, reproducible
  repository-relative references.
- [x] [packet:SI-012-public-source-repository] Added a bounded public-file
  validator to local and CI paths. It checked 129 candidate files; 68 Python
  tests with one environment-limited symlink skip, 36 frontend interactions,
  typecheck/build, browser/static/native contracts, native prerequisites, and
  strict Doctor 0/0 passed before publication. Browser/static/native contract
  probes reported inspected-project writes 0.
- [ ] [packet:SI-012-public-source-repository] Create the public GitHub
  repository, push `main`, and verify visibility, remote HEAD, and workflow state.

## Future / Deferred

- Execute the checked-in matrix on macOS and Ubuntu only when a shared same-RC
  repository run is available; configuration alone is not platform evidence.
- Split future SDAD update work into authenticated engine registry/download,
  read-only project migration preview, Full owner-gated transactional apply,
  and separately signed Inspector product updater packets. Follow
  `UPDATE_AND_MIGRATION.md`; do not silently download engines or write projects.
- Signed beta, installer/updater work, artifact upload, and distribution remain
  owner-gated even after local implementation evidence.

## Release / Production Readiness

Public source-repository creation and push are authorized only for SI-012.
GitHub Releases, signing, artifact/package publishing, deployment, and auto-fix/
write remain owner-gated. Cross-platform and package claims remain blocked until
same-RC evidence exists.

## Recently Closed

- [x] [packet:SI-011-reader-navigation-and-flow-drilldown] Added a compact,
  localized heading navigator with deterministic safe-rendered heading IDs and
  focus transfer, plus a counted routed-document disclosure that defaults open
  on desktop and closed at 720 px.
- [x] [packet:SI-011-reader-navigation-and-flow-drilldown] Made the five
  Development Flow stage cards keyboard-operable changed-file filters with
  honest filtered/total counts, repeated-selection clearing, and an explicit
  all-path reset without changing evidence classification.
- [x] [packet:SI-011-reader-navigation-and-flow-drilldown] Replaced narrow
  Manual/AUTO letters with Phosphor HandPalm/Timer icons and restored explicit
  localized accessible names for Manual, AUTO, and re-scan controls.
- [x] [packet:SI-011-reader-navigation-and-flow-drilldown] Preserved effective
  system Git line-ending semantics instead of forcing `GIT_CONFIG_NOSYSTEM`;
  a deterministic CRLF/`core.autocrlf=true` integration regression now keeps a
  committed repository clean and still reports a Unicode rename correctly.
- [x] [packet:SI-011-reader-navigation-and-flow-drilldown] Software-verified
  locally on Windows on 2026-07-15: 63 Python tests passed with one environment-
  limited symlink skip; 36 frontend interactions, typecheck/build, browser and
  native contracts, authenticated SDAD v3.2.2 staging, 1440x1024 and 720x900
  rendered interaction QA, zero browser warnings/errors, and strict Doctor 0/0
  passed. An isolated unsigned preview contained 1,311 files / 41,944,111 bytes,
  EXE SHA-256 `00710fa4c63b92612e53c890f9319896a14f194a929b9ea41e5f54bc750d2a01`,
  was `NotSigned`, and completed bounded smoke with exit 0. Live re-scan hashes
  for the four control documents stayed unchanged; contract project writes were
  0. The default preview remained owner-open and was not terminated, so this
  packet built under `build/native-si011`. Owner acceptance, release, signing,
  publishing, auto-fix/write, and macOS/Linux execution remain unrecorded.

- [x] [packet:SI-010-consistent-live-flow-state] Unified the repository tree,
  Overview, Development Flow, and Inspector on one active-packet TODO parser,
  including source-section provenance for tagged entries outside Active Work.
- [x] [packet:SI-010-consistent-live-flow-state] Replaced hidden document and
  activity polling with one coherent initial/manual/AUTO/project-switch cycle;
  AUTO runs at one visible non-overlapping 15-second cadence, and selected
  Markdown plus reader scroll position remain stable across a re-scan.
- [x] [packet:SI-010-consistent-live-flow-state] Made Overview Active SPEC and
  eligible relationship paths open the safe central Markdown reader, localized
  visible Git states, and persisted six recent projects in stable per-user app
  preferences with an always-visible safe Clear history action.
- [x] [packet:SI-010-consistent-live-flow-state] Added deterministic,
  source-labeled Scope/Build/Verify/Evidence/Docs-Handoff signals. The newest
  timestamped changed path can mark only a current observation; declared checks
  remain unexecuted evidence and no stage completion is inferred.
- [x] [packet:SI-010-consistent-live-flow-state] Added bounded Rule 5 extraction,
  a human-readable central Markdown preview, exact SHA-256 confirmation, and a
  cancellable system Save As export. Incomplete/stale/mismatched proposals and
  destinations inside the inspected repository are rejected; saved output is a
  local proposal only and never activates or enforces a rule.
- [x] [packet:SI-010-consistent-live-flow-state] Software-verified locally on
  Windows on 2026-07-15: 63 Python tests passed with one environment-limited
  symlink skip; 34 frontend interactions, typecheck/build, browser and native
  contracts, authenticated SDAD v3.2.2 staging, strict Doctor 0/0, rendered
  Korean dark-mode/reference comparison, zero browser console issues, rebuilt
  unsigned one-folder preview, and bounded native smoke exit 0 passed. Project
  writes remained 0. Owner acceptance, signing, publishing, release, automatic
  rule adoption, and macOS/Linux execution remain unrecorded.

- [x] [packet:SI-009-live-project-workspace] Added a system folder picker,
  explicit bounded path paste, current/recent project shortcuts, clear action,
  persistent browser/native storage, and manual/default or explicit
  non-overlapping AUTO 15-second re-scan without project writes.
- [x] [packet:SI-009-live-project-workspace] Rendered Active SPEC and TODO as
  live human-readable Markdown, made eligible routed-document rows/tree items
  open the same reader, and retained safe React elements, bounded authenticated
  reads, visible source/freshness, and recoverable missing/error states.
- [x] [packet:SI-009-live-project-workspace] Added a real-time Development Flow
  and active-packet evidence view sourced from bounded read-only Git worktree
  and recent-commit metadata, packet-tagged TODO entries, repository handoff
  records, and separately labeled declared SDAD facts with honest timestamps.
- [x] [packet:SI-009-live-project-workspace] Software-verified locally on
  Windows: explicit Overview navigation; larger typography and hit areas;
  persisted pointer/keyboard pane resizing; Korean/English and light/dark
  rendering; clipboard and recent-history interactions; 55 Python tests with
  one environment-limited symlink skip; 21 frontend interactions; typecheck,
  production build, browser/static/native contracts, authenticated SDAD 3.2.2
  strict Doctor with 0 errors/0 warnings, an unsigned one-folder rebuild, and a
  bounded native smoke with exit 0 passed on 2026-07-15. The rendered dark-mode
  overview, TODO reader, routed-document reader, and Development Flow use real
  repository data. Owner acceptance and macOS/Linux execution remain unrecorded.

- [x] [packet:SI-008-context-workspace-progress-theme] Software-verified locally
  on Windows: repository parent/leaf selections update matching central and
  right-hand views with a real Overview return tab; authenticated re-scan and
  project-open progress exposes only actual prepare/Doctor/control/integrity/
  report stages, current bounded sources, and eight recent events with no
  percentage or inferred repository work-loop phase; Korean/English light/dark
  themes persist locally. Forty-six Python tests passed with one environment-
  limited symlink skip, eleven frontend interactions passed, typecheck/build,
  browser/static/native contracts, desktop and 720x900 rendered QA, zero browser
  console warnings/errors, authenticated v3.2.2 rebuild, bundle immutability,
  and four bounded native smokes exited 0 on 2026-07-15. The exact unsigned
  preview remains unaccepted, unpublished, and unverified on macOS/Linux.
- [x] [packet:SI-007-missing-state-white-screen] Software-verified locally on
  Windows: a backend-real snapshot with `state.current_handoff: null` first
  reproduced an empty DOM and the `reading 'declared'` React exception, then
  passed the new render/selection regression; eight frontend tests, typecheck,
  build, 43 Python tests, browser/native contracts, and project writes 0 passed.
  Rendered Korean QA showed the missing-state Doctor finding and selectable
  absent handoff with zero console errors. The rebuilt unsigned preview selected
  the reported `ultrasound_viewer` folder through the native picker, rendered
  `Doctor 요약`/`state.missing`, served the new bundled asset, and passed bounded
  smoke on 2026-07-15. macOS/Linux and owner acceptance remain unrecorded.
- [x] [packet:SI-006-korean-localization] Software-verified locally on Windows:
  typed Korean/English catalogs, Korean primary-locale selection, explicit
  switching, versioned reload persistence, `html[lang]`, verbatim repository
  evidence, seven frontend interactions, typecheck/build, loopback/no-write
  validation, 1440x1024 and 720x900 rendered QA, zero console errors, rebuilt
  unsigned one-folder preview, byte-identical bundled frontend, clean v3.2.2
  reprobe, and bounded native smoke exit 0 passed on 2026-07-15. macOS/Linux UI
  execution and owner acceptance are not recorded.
- [packet:SI-005-native-preview] Software-verified locally on Windows: 43 Python
  tests (one environment-limited symlink skip), five frontend tests, typecheck,
  production build, native contract validation, authenticated v3.2.2 staging,
  PyInstaller 6.21.0 one-folder build, bundled-engine reprobe, and a two-second
  hidden pywebview launch/close smoke exited 0 on 2026-07-15. The executable is
  unsigned. macOS/Linux runner results and owner acceptance are not recorded.
- [packet:SI-004-static-report] Evidence-ready locally: six report tests and a
  real v3.2.2 validation proved escaped active-content-free HTML, path/evidence
  redaction, outside-project atomic output, overwrite protection, snapshot-only
  rendering, and project writes 0 on 2026-07-15. Owner acceptance is not recorded.
- [packet:SI-003-browser-mvp] Evidence-ready locally on Windows: 27 Python
  tests, five frontend interaction tests, typecheck, production build, hardened
  browser-contract probe, 1440x1024 and 720x900 rendered QA, filter/selection,
  Raw JSON, re-scan, clipboard, project-dialog interactions, and zero browser
  console errors passed on 2026-07-15. macOS/Linux browser smoke and owner
  acceptance are not recorded.
- [packet:SI-002-headless-core] Evidence-ready: snapshot schema 1, authenticated
  release-tree execution, schema adapters, path controls, no-write assertion,
  malformed/version/exit handling, 21 tests, Packet 0 validation, and live
  v3.2.2 CLI inspection passed locally on 2026-07-15. One Windows symlink test
  was skipped because the environment could not create symlinks; hard-link
  rejection passed. Owner acceptance is not recorded.
- [packet:design-selection] Owner selected concept 3, Split Inspector, on
  2026-07-15; its immutable reference and interaction anatomy are recorded in
  `DESIGN_REFERENCE.md`.
- [packet:SI-001-contract-and-fixtures] Evidence-ready: normalized exit 0/1/2
  reports were captured for clean released v3.2.1 and v3.2.2 tags; manifest
  hashes, offline validation, live tag-archive recapture, four unit tests, and
  Doctor 3.2.2 strict all passed on 2026-07-15. Owner acceptance is not recorded.
