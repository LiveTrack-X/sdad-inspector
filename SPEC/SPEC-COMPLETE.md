# SPEC COMPLETE

Status: Canonical integrated SPEC
Scope: Current product and implementation baseline

`COMPLETE` means integrated baseline, not immutable or automatically active.
For a stateful packet, `sdad-state.yaml#active_spec` selects the single
normative SPEC entrypoint.

## SPEC Authority And Lineage

This integrated baseline is not immutable, and it is not automatically active;
state selects the normative entrypoint.

An additional SPEC does not become authority merely because it is newer, has
`FINAL` or `COMPLETE` in its name, or exists under `SPEC/`. Requested action and
owner intent matter: a SPEC supplied as current requirements is a change
request, while review/draft/reference-only intent is not. Hold affected
implementation while comparing it with the active acceptance boundary; do not
demote it to proposal/reference merely because state has not been updated yet.
A SPEC only discovered in the repository may remain non-authoritative, but the
packet may continue only after it is confirmed nonconflicting. Then classify
the result as an amendment, bounded supplement, replacement, or proposal.

- Amendment: update the current active SPEC inside the existing acceptance
  boundary.
- Bounded supplement: the active SPEC links its exact path and scope; this
  active entrypoint controls conflicts and the baseline controls everything
  outside the declared override.
- Replacement: record owner scope/acceptance, name the superseded path or exact
  headings, and switch `active_spec` in the packet transaction.
- Proposal/reference: retain it as non-authoritative input until promoted.

For a non-terminal packet, an owner-requested change inside the same objective
and acceptance boundary may amend or supplement the active SPEC in the same
packet; invalidate and rerun affected evidence. A material objective,
acceptance, protected-boundary, or authorization-term change uses a new packet.
If intent or overlap cannot be determined, ask one blocking question before
affected implementation. A terminal accepted boundary is never reopened.

New additional or replacement SPECs start with this exact metadata block:

```markdown
Status: Proposal | Active | Superseded | Reference
Baseline: SPEC/path.md
Baseline revision: commit/tree/digest | Unpinned proposal
Effective packet: WP-EXAMPLE | Unassigned
Supersedes:
- SPEC/path.md#exact-heading | None (additive)
```

`Effective packet` records the first packet that activates this SPEC revision;
do not rewrite it to follow the current packet. Use `Active` only after exact
incorporation or pointer switch. Existing
single-SPEC projects remain valid without retrofitting metadata. A material
requirement change after owner acceptance uses a new, never-reused packet ID
and new validation; it does not rewrite old acceptance to cover new scope.
Pin the baseline revision when a supplement participates in a terminal packet;
an unpinned proposal remains non-authoritative.

`Active` on a supplement means the state-declared entrypoint incorporated it;
it does not create a second normative entrypoint. Normative supplements must be
readable repository-local paths. Keep lineage acyclic: a SPEC cannot supersede
itself, and overlapping supplements require explicit precedence in the active
entrypoint before implementation. External documents remain references until
their accepted requirements are incorporated repository-locally.

Current lineage:

- `../SDAD_INSPECTOR_PRODUCT_PLAN.md` is the owner-requested planning input
  incorporated by packet `SI-001-contract-and-fixtures` on 2026-07-15.
- This file is the single normative entrypoint. The planning input remains an
  unchanged design source; this SPEC controls if wording later conflicts.
- No competing active SPEC or normative supplement is known.

Do not split a SPEC merely because work continues after `COMPLETE`. Split when
targeted reads are no longer practical, independent domains need different
packets, or parallel edits repeatedly conflict. Keep `active_spec` as the short
normative entrypoint and link bounded supplements with exact inherited and
overridden scope; do not duplicate shared acceptance across leaf files.

## Product Definition

SDAD Inspector is a local, read-only inspection product for SDAD repositories.
It makes the active packet, authority chain, validation contract, Doctor
findings, continuity state, and engine provenance understandable without
executing project commands or changing the inspected repository. The intended
product path is a Python core with a React/TypeScript browser UI, followed only
after evidence by an optional pywebview/PyInstaller desktop shell.

## Origin / Pain

SDAD control state is precise but distributed across YAML, Markdown, Git, and
Doctor JSON. Owners and reviewers need a cross-platform view that answers what
is active, authoritative, blocked, validated, and safe to claim without first
reconstructing the protocol by hand.

## Owner Control Model

The owner controls product direction, final acceptance, release, signing,
publishing, and every auto-fix or write capability. Local read-only code and
fixture work may proceed inside the active packet, but none of those protected
actions is authorized by implementation or passing tests.

## Principles

- The owner controls direction and final acceptance.
- AI output is not completion evidence by itself.
- The state-declared active SPEC entrypoint drives implementation.
- Tests, docs, and reproducible commands prove behavior.
- Future ideas stay out of active work until promoted.
- Current active SPEC sections override older historical sections.
- Obvious but consequential rules must be written down.
- Fuzzy plans should be checked against repository evidence before owner
  clarification.
- Partial, degraded, skipped, or unverified behavior must be labeled.

## Current Architecture

The verified Python core authenticates clean released SDAD engines, invokes
Doctor without a shell, normalizes report/state contracts into snapshot schema
1, preserves raw evidence, and bounds every project read. A `127.0.0.1`-only
Python HTTP surface serves the React/TypeScript/Vite Split Inspector to both a
normal browser and the optional pywebview window. The renderer consumes only
typed snapshot data; it has no direct filesystem, subprocess, or Python bridge
access. Frozen Doctor calls use a fixed internal child entrypoint that accepts
only the bundled engine and reauthenticates its whole release tree before use.

## Version Lanes

The initial compatibility lane targets released SDAD Doctor cores 3.2.1 and
3.2.2, report schemas 1 and 2, and state schemas 1 and 2. Inspector versions
remain independent from SDAD versions. A future engine or schema requires a
new compatibility packet and fixtures before its support claim is allowed.

## Risk Domains

- Repository path containment, symlink handling, and untrusted text rendering.
- Accidental execution of declared validation commands or repository content.
- Sensitive files and evidence leakage.
- Doctor/report/state version negotiation and stale provenance.
- Windows, macOS, and Linux packaging claims that exceed tested evidence.
- Release, signing, publishing, and any future write/repair surface.

## Active Scope

Packet `SI-013-alpha-release` is the owner-directed 2026-07-15 public alpha
release pass. The product package version is `0.0.1a2`, the immutable release
Git tag is `v0.0.1-alpha.2`, and the public release title is
`SDAD Inspector 0.0.1 alpha`. The authoritative owner decision is recorded once
in `docs/claim-registry.md`.

The earlier `v0.0.1-alpha.1` tag is retained as failed validation history: its
workflow published no GitHub Release or assets and the tag is never moved.

The same tagged commit must run the bounded test, frontend build, native build,
and launch-smoke path on GitHub-hosted Windows, macOS, and Linux runners. Native
release builds use CPython 3.12 and PyInstaller one-file mode so the selected
platform archive contains exactly one self-contained executable and no adjacent
`_internal` runtime tree. A separate clean hosted-runner job must download,
extract, inspect, and bounded-smoke that archive without installing the product's
Python dependencies. The workflow publishes exactly three platform archives and
one `SHA256SUMS` file to an explicitly marked GitHub prerelease. Every archive
and the release notes must say that this alpha is unsigned and experimental;
evidence from the hosted runners is not a general stable-support claim.

The public README must explain what the Inspector does, how to attach it to an
SDAD project, its read-only boundary, supported SDAD contract versions, release
and source-run instructions, repository architecture, validation commands, and
known alpha limitations. A compatible project has a root `sdad-state.yaml` and
the active SPEC/routed documents named by that state. The bundled runtime and
primary baseline are official SDAD Protocol `v3.2.2`; Doctor reports from
`3.2.1` and `3.2.2` plus state schemas 1 and 2 remain the bounded compatibility
lane already covered by fixtures.

Repository cleanup removes historical `design/qa` captures, their local QA
ledger, and machine-local npm configuration while retaining the owner-selected design reference,
normative SPEC/SDAD controls, product source, tests, scripts, and public release
automation. Runtime, dependency, cache, editor, build, and release-output files
remain ignored and outside source publication.

Cross-platform path containment must compare canonical roots and candidates so
macOS `/var` versus `/private/var` aliases and Windows long-name versus 8.3-name
aliases do not hide Git status or reject an otherwise contained project. Tests
must compare canonical production outputs without weakening traversal or
symlink protections.

This packet is a one-off owner-authorized unsigned GitHub alpha prerelease. It
does not authorize a stable release, installer, updater, code signing,
notarization, package-registry publication, deployment, automatic project
write, or broad operating-system support claim. No license grant is inferred
from public visibility.

Prior packet `SI-012-public-source-repository` created, preflighted, and pushed
the public `LiveTrack-X/sdad-inspector` source repository. Its first hosted
matrix exposed the canonical-path defect now routed into this packet.

Prior packet `SI-011-reader-navigation-and-flow-drilldown` was the owner-directed
UI/UX and functionality improvement pass. It preserved the selected Split
Inspector visual source, three-pane information architecture, source-language
evidence boundary, coherent refresh cycle, and inspected-repository read-only
contract.

Long live Markdown documents must expose a compact localized heading navigator
derived only from the already bounded Markdown content. Selecting an entry
moves keyboard focus and the center reader to the matching rendered heading;
the generated heading identifiers must be deterministic within the document
and must not interpret repository HTML. The routed-document selector remains
available as an explicit disclosure, defaults open at readable desktop widths
and closed at narrow widths, and exposes its current count and expanded state.

The five Development Flow evidence classifications remain non-causal signals,
but their existing cards become keyboard-operable changed-file filters. One
selected stage shows only paths classified to that stage, reports the filtered
and total counts, and can be selected again or cleared to restore all bounded
paths. Filtering never changes classification, timestamps, TODO evidence, Git
probes, or phase-completion claims. At narrow widths the Manual and AUTO scan
controls use the established Phosphor icon family rather than untranslated
single-letter replacements while retaining localized accessible names.

The fixed read-only Git probes must preserve the owner's effective system Git
configuration when interpreting tracked-file line endings. In particular, the
probe must not force `GIT_CONFIG_NOSYSTEM` and then misreport a repository
committed under a system-level `core.autocrlf` policy as modified. The existing
fixed arguments, `shell=False`, disabled optional locks/fsmonitor/untracked
cache, timeouts, output limits, and no-content-read boundary remain unchanged.

Prior packet `SI-010-consistent-live-flow-state` corrected the live workspace contract
without expanding the read-only boundary. The left TODO count, Overview packet
TODO, Development Flow checklist, and inspector selection facts must use one
parsed set of entries tagged `[packet:<active-id>]` across the bounded TODO
document; the Doctor `Active Work` ledger count must not be presented as the
active-packet count when tagged work also appears in another section. Packet
work retains its source section so the UI can explain the total.

Initial load, manual re-scan, explicit AUTO re-scan, and project switching must
refresh the normalized snapshot, eligible live Markdown, and bounded development
activity as one non-overlapping workspace cycle. Manual mode performs no hidden
document or activity polling. AUTO remains one visible 15-second cadence and
pauses while hidden. A successful refresh swaps the next coherent workspace
state without clearing the current document, selection, reader scroll position,
or stable panel geometry; a partial auxiliary read failure retains the last good
document or activity result with bounded stale/unavailable evidence.

Every eligible Markdown path shown in Overview, including the Active SPEC
relationship, must be an actual keyboard-operable control that opens the same
central safe Markdown reader used by the repository tree. Refresh preserves the
selected document when it remains eligible.

Development Flow presents five evidence classifications: Scope, Build, Verify,
Evidence, and Docs/Handoff. A stage may be `declared`, `observed`, `current
observation`, or `no signal`. `Current observation` comes only from the newest
bounded changed-file timestamp and its path classification; it is not proof that
the stage ran, passed, completed, or caused the change. Declared validation stays
explicitly unexecuted. Each stage shows its basis and the view keeps the existing
observed-versus-declared caveat.

Git porcelain codes remain available only as diagnostic detail. Visible status
badges use localized human labels such as New file, Modified, Added, Deleted,
Renamed, Copied, or Conflict; in Korean they use the corresponding Korean label.

Recent projects are stored in a bounded, versioned Inspector preference file at
the operating system's per-user application-data location rather than relying on
the loopback origin's port-scoped browser storage. Only successful explicit
project opens update up to six path/name/timestamp records. The current project
is excluded from the visible recent list; after switching, the prior project is
immediately available. The project dialog always exposes a localized Clear
history action, disabled only when the list is empty. Clearing removes the
bounded preference records and never touches an inspected repository.

The owner has also directed a bounded Rule 5 candidate workflow. Inspector may
read the Active Findings section of `review-findings.md`, extract each explicit
finding plus any labeled root-cause/control/enforcement/regression/review fields,
and show missing fields as unknown/blocking. The editor and generated Markdown
preview must make the proposed operational rule, its origin, trigger/non-trigger,
root cause, exceptions, enforcement, regression evidence, limits, and later
Keep/Refine/Merge/Retire condition human-readable before any save.

Extraction produces one bounded versioned Markdown proposal in the central safe
viewer. Local export requires complete core fields, a visible reviewed-preview
confirmation, and an explicit user click. The system Save As dialog chooses the
destination and may be cancelled without creating a file. The service regenerates
the proposal and requires its SHA-256 to match the exact viewer preview before an
atomic local `.md` write; it never accepts arbitrary renderer HTML or a silent
default path. This exported record is a proposal, not an active repository rule
or owner acceptance. Export does not modify the inspected repository, `AGENTS.md`,
active SPEC/state, operating rules, validators, tests, commits, or remotes.
Adopting, merging, refining, retiring, or enforcing an exported proposal remains
a separate owner-gated action.

The prior packet `SI-009-live-project-workspace` established project selection
and current-work evidence. It makes project selection and current work
evidence faster to use without turning Inspector into an agent runtime. The
project dialog must keep direct path entry while adding a system folder picker,
an explicit paste action, the current project, and up to six versioned locally
stored recent projects with a visible clear action. Native webview storage must
persist across application restarts. Folder selection, clipboard reading, and
recent-path storage happen only after explicit owner interaction; clipboard
text is bounded to one path-sized value and is never read in the background.

Selecting Active SPEC, TODO, or an eligible routed Markdown document in the
repository tree or routed-document list must render the actual bounded document
in the central workspace instead of a JSON or metadata-only summary. The
renderer must use React elements, never raw HTML or `dangerouslySetInnerHTML`,
and must present headings, paragraphs, lists, task items, tables, blockquotes,
links, and code legibly in both themes. An authenticated no-store live-document
endpoint may refresh only the declared Active SPEC, fixed TODO/findings ledgers,
current handoff, and state-declared routed Markdown paths; the UI polls it while
a document is visible and labels the read time and source.

The repository tree must also expose a Development Flow view. While it is
visible, fixed read-only Git probes may report bounded worktree path metadata,
status codes, changed counts, scan duration, and a bounded recent commit log.
They use `shell=False`, disable optional Git locks and fsmonitor, apply timeout/
output/entry limits, never read changed-file contents, and never execute owner-
declared validation. The human-readable view combines that observed signal with
separately labeled declared packet, SPEC, validation, evidence, and handoff
facts. Repository-local handoff history is limited to declared/routed handoff
documents plus direct Markdown children of the fixed conventional
`docs/sdad/handoffs` or `docs/handoffs` directories, with bounded metadata and
short content summaries. Commit author identity is not displayed. Absolute and relative timestamps identify commit time, handoff file
modification time, and observed changed-file modification time; Inspector never
guesses an unrecorded work start or completion time.

The active packet view must show its tagged open and completed TODO entries,
repository handoff records, recent Git commits, and worktree paths observed
while the packet is active. A changed path is not attributed causally to the
packet unless repository evidence says so. Completed work comes only from
checked TODO entries tagged `[packet:<active-id>]`; current changes and commit
history remain separate evidence classes. The UI must not fabricate risk scores,
percentages, commits, agent activity, or Plan/Route/Implement/Verify/Report
completion. Live refresh failures retain the last good view and show a bounded
unavailable/stale state.

Re-scan is manual by default. The owner may explicitly enable a locally stored
`AUTO 15s` mode that displays a countdown and invokes the same authenticated
read-only re-scan at most once every 15 seconds while the document is visible.
Automatic and manual scans never overlap. A manual scan or project switch resets
the countdown, disabling AUTO cancels it, and background pages do not scan.

The existing Split Inspector layout remains authoritative, but text, row hit
areas, line height, and contrast must be increased across the command bar,
repository tree, Markdown reader, progress/timeline, and inspector panes. The
desktop center reader receives the dominant width; narrow layouts preserve
readability and keyboard/touch operation without replacing the three-pane
information architecture. An explicit Overview item is the first repository-
tree destination. The two vertical pane boundaries are pointer- and keyboard-
resizable within readable limits, support a reset, and store only their local
width preference; drawer behavior replaces resizing at narrow widths.

## Non-Goals

- No automatic translation service, network lookup, or mutation of repository
  evidence; code, paths, packet IDs, commands, raw JSON, and owner-authored text
  stay in their source language.
- No support claim for languages beyond Korean and English in this packet.
- No installer, updater, signing, notarization, stable release, package-registry
  publication, or deployment. The only distribution in this packet is the
  explicitly labeled unsigned `0.0.1 alpha` GitHub prerelease.
- No owner-declared validation command execution, auto-fix, or project write;
  the explicitly confirmed Rule 5 export writes only the owner-selected local
  `.md` destination. No network or telemetry. The only new subprocesses are the fixed read-only Git
  status and recent-commit metadata probes described in the active scope.
- No runtime engine download and no direct renderer filesystem bridge.
- No Windows/macOS/Linux support claim from local fixture evidence alone.
- No change to SDAD upstream and no new upstream snapshot CLI.

## Risks

- A normalized fixture can accidentally erase a meaningful schema difference.
- A local tag can be mistaken for remote release provenance.
- Structural Doctor success can be overstated as product correctness.
- Future UI or packaging work can silently cross the read-only boundary.
- Clipboard access, persistent recent paths, broad Git output, or rendered
  repository Markdown can leak more than the explicit interaction requires.

## Roadmap

1. Freeze released contracts and fixtures.
2. Build the headless Python inspection core.
3. Select and specify one evidence-backed product UI direction.
4. Build the browser MVP and static sanitized report.
5. Validate a native preview independently on Windows, macOS, and Linux.
6. Enter signed beta only through the release/signing/publishing owner gates.

## Decision Records

Record durable decisions under `SPEC/adr/`. Use ADRs when future agents need to
know why a decision was made, what alternatives were rejected, and what older
SPEC material was superseded.
A decision normally deserves an ADR only when it is hard to reverse, would
surprise a future maintainer without context, and represents a real tradeoff.

## Domain Language

- **Doctor core**: the released SDAD checkout whose `scripts/sdad.py` creates a report.
- **Normalized snapshot**: Inspector-owned, read-only data derived from Doctor
  JSON and bounded control-file metadata; it is not SDAD state authority.
- **Support claim**: wording allowed only for the exact engine, schema,
  environment, and evidence tier recorded in the claim registry.

## Completion Criteria

Packet `SI-013-alpha-release` is evidence-ready when the README and source tree
match the active release boundary; canonical-path regressions pass on all three
hosted operating systems; public-file, Python, frontend, browser, native,
release-contract, and strict Doctor checks pass locally; and the exact tagged
commit builds one CPython 3.12-based executable per platform and each downloaded
single-file archive smoke-launches in a separate clean Windows, macOS, or Linux
job. The release job must publish three intentionally named platform archives
and `SHA256SUMS` to a GitHub prerelease titled `SDAD Inspector 0.0.1 alpha`.
Completion requires
remote verification that the tag targets the tested commit, every expected
asset exists, downloaded asset hashes match the published checksum file, and
the release prominently states its unsigned experimental limitations.

Prior packet `SI-012-public-source-repository` was complete when the bounded
public source tree was pushed to a `PUBLIC` repository on `main`, local and
remote source commits matched, and the first checked-in matrix started. That
matrix was configuration evidence only until its failures were handled here.

Prior packet `SI-011-reader-navigation-and-flow-drilldown` was locally evidence-
ready when desktop and narrow rendered QA showed the selected Split Inspector
visual system with no clipped or obscured controls; the Markdown heading
navigator moved focus to exact safe-rendered headings; the routed-document
disclosure was keyboard-operable and responsive; Development Flow stage
selection filtered only the changed-file list with honest filtered/total counts
and an all-path reset; narrow scan controls retained localized accessible names;
and the owner-effective Git line-ending regression, frontend checks, full Python
suite, browser/native contracts, rendered interaction pass, and strict Doctor
all passed locally on Windows.

Prior packet `SI-010-consistent-live-flow-state` was locally evidence-ready when one
active-packet TODO parser supplies the left-tree count, Overview checklist,
Development Flow checklist, and selection metadata; deliberately different
whole-ledger and packet-tagged fixture counts cannot produce conflicting visible
numbers. Manual mode makes no auxiliary refresh after the initial coherent load.
Manual and AUTO scans refresh snapshot, Markdown, and activity together, never
overlap, preserve a selected Markdown reader and scroll position, and do not
blank or visibly collapse the workspace during a successful update.

Overview Active SPEC and eligible relationship paths must open the matching safe
Markdown document by pointer and keyboard. Changed-file badges must show
localized labels rather than raw `??` or porcelain letters while exposing the raw
code in non-primary detail. The five-stage Development Flow must classify fixed
fixtures deterministically, identify a current observation only from the newest
timestamped changed path, expose its source basis, and never claim verification,
evidence, handoff, or phase completion. Korean and English, light and dark,
desktop and narrow rendered QA must remain legible and stable.
Recent projects must survive a new service/browser origin by loading from the
same injected per-user preference store, reject malformed or oversized data,
update only after a successful explicit open, and clear through an authenticated
bounded endpoint. Tests must prove the previous project appears after switching,
the current project is filtered, the clear action remains visible, and neither
operation changes either inspected repository.
Rule 5 tests must cover bounded finding extraction, structured field recovery,
unknown/blocking fields, exact preview text and digest, explicit confirmation,
Save As cancellation, extension normalization, atomic local export, and zero
repository writes. Frontend tests must prove the candidate is
readable/editable, the exact Markdown preview is visible, save is disabled until
required fields and confirmation are present, and a successful save reports the
owner-selected local path without presenting the proposal as active.

Packet `SI-009-live-project-workspace` is locally evidence-ready when the system
picker can return or cancel without changing projects, explicit paste fills the
path without background clipboard reads, successful opens update a bounded
recent list, and clearing removes it. Active SPEC and TODO must display live,
human-readable, safely escaped Markdown; routed document rows/tree items must
open their eligible Markdown. Documents update after a bounded source change
without a full Doctor run. Missing/unreadable documents remain recoverable.

The Development Flow and active packet views must update from authenticated
no-store endpoints, bound Git timeout/output/entry counts, show changed-path,
recent-commit, packet-tagged TODO, and handoff history with source timestamps,
and keep observed versus declared facts visually distinct. Manual mode is the
default; explicit AUTO mode displays and resets a 15-second countdown, pauses
while hidden, and never overlaps a scan. Non-Git projects, clean worktrees,
rename paths, unusual Unicode paths, unavailable Git, and failed probes require
tests. Existing project writes remain zero.

Frontend tests must cover picker/cancel contracts, paste success/failure,
versioned recent-project persistence/clear, safe Markdown including raw HTML,
live document/activity refresh, packet evidence parsing, Git/handoff timelines,
manual/AUTO timing, Overview navigation, and persisted pointer/keyboard pane
resizing. Python tests must cover route authorization, bounded
clipboard/picker behavior, live document containment, Git parsing/limits, and
no-write behavior. Typecheck, production build, browser/
native contracts, full suites, rendered desktop/narrow QA, and final strict
Doctor must pass. Windows evidence does not establish macOS/Linux execution.
Signing, publishing, release, project-write behavior, and owner acceptance
remain gated.

## Release / Production Readiness Gate

A stable or signed public release requires the same release candidate to pass
install/launch, project selection, Doctor probing, exit 0/1/2 inspection,
findings rendering, no-write assertion, and clean shutdown on Windows, macOS,
and Linux. Package identity, security review, upgrade/uninstall/rollback
evidence, signing or notarization, known limitations, fresh review, and explicit
owner authorization are additional gates.

For SI-013 only, the owner explicitly authorized an unsigned alpha prerelease.
Its narrower gate requires a same-commit three-OS CI matrix, bounded native
launch smoke, one CPython 3.12-based executable inside each of three archives,
post-download smoke on separate clean hosted runners, published SHA-256 hashes,
prominent unsigned and experimental limitations, and remote tag/asset/hash
verification. This exception does not weaken the stable, signed, installer,
updater, or deployment gate. Packet 0 satisfies none of those broader gates.
