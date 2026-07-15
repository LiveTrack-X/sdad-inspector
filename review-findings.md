# Review Findings

Status: Active
Scope: Active bugs and review findings only

## Active Findings

- [High] [packet:SI-013-alpha-release] FIND-SI-013-001 — GitHub Actions run
  `29401532720` failed all three jobs because `safe_project_path` resolved each
  candidate but compared it to a noncanonical temporary root. macOS exposed
  `/var` versus `/private/var`; Windows exposed an 8.3 alias versus the long
  profile name. Valid contained Git paths were filtered, live documents were
  rejected, and tests compared canonical production outputs to alias fixtures.
  Release is blocked until the root is canonicalized before containment and
  symlink checks, canonical expectations are regression-tested, and the same
  commit passes the Windows/macOS/Linux matrix.

- [High] [packet:SI-013-alpha-release] FIND-SI-013-002 — A Windows one-folder
  preview copied to another computer failed before application startup with
  `Failed to load Python DLL ... _internal\\python313.dll`; the subsequent local
  Conda Python 3.13 rebuild also timed out in bounded native smoke. Release is
  blocked until packaging uses official CPython 3.12 one-file mode, every
  platform archive contains exactly one executable, and a separate clean
  hosted-runner job downloads, extracts, and smoke-launches that exact archive.

- [Medium] [packet:SI-013-alpha-release] FIND-SI-013-003 — Actions run
  `29409019274` passed the complete Windows one-file build path but stopped in
  Python tests on macOS and Linux before native packaging. The macOS no-write
  fingerprint raced with Git's transient `.git/objects/maintenance.lock`; the
  Linux preference-path helper treated an explicitly supplied empty environment
  mapping as absent and read the runner's real `XDG_CONFIG_HOME`. CI is blocked
  until working-tree fingerprints exclude Git-internal metadata, explicit empty
  mappings remain authoritative, and the same tests pass on all three runners.

- [High] [packet:SI-013-alpha-release] FIND-SI-013-004 — Actions run
  `29409284793` passed all three Python/frontend suites and the complete Windows
  one-file build, but macOS/Linux stopped while reauthenticating the copied SDAD
  engine. The frozen whole-tree hash treated CRLF and LF checkouts of
  Git-declared text as different releases. Release is blocked until supported
  text paths hash with CRLF normalized to LF, binary assets remain byte-exact,
  both released engine constants are recaptured from official archives, and the
  copied engine authenticates on all three runners.

- [Medium] [packet:SI-013-alpha-release] FIND-SI-013-005 — Actions run
  `29409811078` built, smoke-launched, and archived the Windows/macOS one-file
  binaries and built the Linux binary, but Linux first failed on missing
  `libEGL.so.1`. Run `29410068845` then reached the Linux launch after adding a
  minimal EGL/GL/XCB set, but Qt's `xcb` plugin still could not load because its
  remaining X11/XCB runtime dependencies were absent. CI is blocked until every
  Linux build and downloaded-artifact job installs the same complete Qt X11
  runtime baseline and public limitations distinguish embedded Python from
  required operating-system display services.

Do not leave closed findings in this section. Move fixed or accepted items to
`## Recently Closed` before an evidence checkpoint or handoff.

## Future / Deferred Findings

Use this only for unresolved findings owned by a noncurrent split parent or
inactive sibling packet. Preserve the original finding text and any ID,
severity, packet marker, and evidence link; add the split-decision link, defer
reason, and explicit revisit trigger. This is not closure. When that packet
becomes current, move its intact finding back to `## Active Findings` before
work or acceptance; do not keep two copies.

## Severity Gate

- Critical findings block release or production readiness.
- High-risk domain findings block the affected slice until reviewed and tested.
- Release candidates should reach Critical 0 before owner acceptance.

## Recently Closed

- [FIND-SI-012-001] [packet:SI-012-public-source-repository] Fixed and
  regression-tested before publication: public candidate files contained local
  absolute QA/source paths and a machine-specific npm cache path. The paths are
  now repository-relative or public upstream URLs. A reusable preflight rejects
  personal absolute paths, generated/local-only directories, sensitive
  filenames, files above 50 MiB, private-key markers, and high-confidence
  GitHub/AWS credential forms while retaining one explicit synthetic operating-
  system path fixture. The same check runs in the public CI workflow. This is a
  bounded high-confidence check, not a claim to detect every possible secret.

- [FIND-SI-011-001] [packet:SI-011-reader-navigation-and-flow-drilldown] Fixed,
  interaction-tested, and rendered at 1440x1024 and 720x900: long bounded
  Markdown now has safe heading navigation, and routed documents use a counted
  responsive disclosure that no longer consumes the first narrow viewport.
- [FIND-SI-011-002] [packet:SI-011-reader-navigation-and-flow-drilldown] Fixed,
  interaction-tested, and rendered: every Development Flow stage is a pressed-
  state filter, the list reports filtered/total counts, and the all-path reset
  restores the unchanged bounded classification set.
- [FIND-SI-011-003] [packet:SI-011-reader-navigation-and-flow-drilldown] Fixed and
  rendered: narrow Manual/AUTO controls use the established Phosphor icons, and
  explicit Korean/English accessible names remain after visible labels hide.
- [FIND-SI-011-004] [packet:SI-011-reader-navigation-and-flow-drilldown] Fixed and
  regression-tested: the Git probe preserves the effective system line-ending
  policy, so a CRLF repository committed under `core.autocrlf=true` remains
  clean while Unicode rename detection and read-only probe limits still pass.

- [FIND-SI-010-001] [packet:SI-010-consistent-live-flow-state] Fixed and
  regression-tested: one packet-tagged TODO parser now supplies repository,
  Overview, Development Flow, and Inspector totals while retaining source
  sections. A fixture with a different Doctor ledger count no longer produces
  conflicting visible packet counts.
- [FIND-SI-010-002] [packet:SI-010-consistent-live-flow-state] Fixed and
  regression-tested: initial load, manual re-scan, explicit AUTO, and project
  switch now refresh snapshot/documents/activity/Rule-5 state coherently. Manual
  has no hidden auxiliary timers, AUTO runs once per non-overlapping 15-second
  interval, and the selected Markdown reader plus its scroll position survive.
- [FIND-SI-010-003] [packet:SI-010-consistent-live-flow-state] Fixed and rendered:
  Active SPEC and eligible Overview relationship paths are keyboard-operable
  controls that open the same safe central Markdown reader as the tree.
- [FIND-SI-010-004] [packet:SI-010-consistent-live-flow-state] Fixed and
  regression-tested: visible Git badges use localized human labels, and the
  five-stage Development Flow derives a current observation only from the newest
  timestamped changed path while keeping raw porcelain and evidence limits in
  secondary detail.
- [FIND-SI-010-005] [packet:SI-010-consistent-live-flow-state] Fixed and exercised
  with two real projects: successful opens persist up to six recent projects in
  the stable per-user preference file, immediately expose the previous project,
  and keep Clear history visible and safely disabled when empty.
- [FIND-SI-010-006] [packet:SI-010-consistent-live-flow-state] Fixed and
  regression-tested: a complete active finding can become one bounded Rule 5
  proposal whose lifecycle fields, origin, exact Markdown, and SHA-256 are shown
  before confirmation. The server rechecks the active source and digest, the
  system Save As dialog is cancellable, exact bytes are written atomically only
  outside the inspected repository, and the proposal is never activated.
  Root cause: The product exposed findings but had no bounded proposal model,
  preview identity, or owner-selected local export boundary for the Rule 5 loop.
  Operational rule: A Rule 5 export must be a complete proposal shown in the
  central Markdown viewer, explicitly confirmed against its digest, and saved
  only through a cancellable system Save As dialog outside the inspected
  repository; it never activates the rule or changes the inspected repository.
  Trigger: An active finding records repeated pain or one high-risk failure and
  the owner wants to extract a durable-control proposal.
  Non-trigger: Ordinary findings that have not reached the repeated-pain or
  high-risk threshold, or requests to auto-apply a rule without an owner gate.
  Exceptions: None for preview matching, explicit confirmation, cancellation,
  or repository immutability.
  Enforcement: Server-side source and preview digest checks, one explicit
  confirmation flag, a system Save As picker, bounded atomic `.md` writing, and
  closed authenticated loopback routes.
  Regression evidence: Python and frontend tests prove incomplete candidates
  block extraction, cancel writes nothing, stale sources and mismatched previews
  are rejected, saved bytes equal viewed Markdown, inside-repository destinations
  are rejected, and the inspected repository fingerprint stays unchanged.
  Limits: Export is a proposal, not owner acceptance, active repository policy,
  automatic enforcement, publishing, or field validation.
  Review condition: Keep after successful owner field use; Refine if required
  fields remain confusing; Merge if another export rule fully overlaps it; or
  Retire if SDAD provides an equivalent authenticated proposal-export contract.

- [FIND-SI-007-001] [packet:SI-007-missing-state-white-screen] Fixed and
  regression-tested: selecting a folder without readable SDAD state returns the
  valid normalized contract `state.current_handoff: null`, while the frontend
  type and repository tree had assumed an object and crashed the first render.
  The type now preserves nullability, tree/detail selection is null-safe, and a
  backend-real missing-state interaction test fails on the old behavior and
  passes on the fix. Live browser QA changed empty DOM plus `reading 'declared'`
  into the Korean diagnostic surface with zero console errors; the rebuilt
  Windows preview repeated the reported native folder-picker flow successfully.
- [FIND-SI-005-001] [packet:SI-005-native-preview] Fixed and regression-tested:
  a frozen application cannot use `sys.executable -I script.py` as though its
  PyInstaller GUI executable were a general Python interpreter. The first
  Windows smoke recursed and timed out. Frozen Doctor calls now route through a
  fixed internal flag that accepts only the bundled engine path; the child
  reauthenticates the complete release tree before `runpy`, and source mode
  retains isolated interpreter execution. The rebuilt artifact exited 0 in the
  bounded hidden smoke on 2026-07-15.
- [FIND-SI-005-002] [packet:SI-005-native-preview] Fixed and regression-tested:
  Python isolated mode ignores `PYTHONDONTWRITEBYTECODE`, so release probes that
  used `-I` alone could create ignored `__pycache__` files in an engine stage
  and copy them into the preview. Source probes now use `-I -B`; staging rejects
  Git/bytecode/runtime artifacts before reuse and after both authentication
  points. A new digest-keyed clean stage is used for the final build.
- Move old closed history to archive when it stops affecting current decisions.

## Guardrails

Stop feature work if critical tests fail, security boundaries regress, or production-readiness evidence is missing.
