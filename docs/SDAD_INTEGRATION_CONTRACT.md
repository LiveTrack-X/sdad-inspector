# SDAD Integration Contract

Status: Active
Observed: 2026-07-18

## Project Attachment Contract

Point Inspector at a repository root containing a readable `sdad-state.yaml`
using SDAD state schema 1 or 2. The declared `active_spec` is the normative
document entrypoint. Inspector also reads the conventional TODO and findings
ledgers, an existing declared handoff, and Markdown paths in `routed_docs` through
bounded, repository-contained reads. These documents can be opened in the local
read-only viewer; availability is not verification or owner acceptance.

An inspected project may optionally identify the exact current work for display:

```markdown
- [ ] [packet:APP-001] [phase:Implement] [current] Implement the bounded change.
```

Only an open TODO whose packet ID equals `active_packet.id` and which declares
both `[current]` and one official `Plan|Route|Implement|Verify|Report` phase can
highlight the official loop. Missing, completed, invalid, or conflicting markers
remain undeclared/ambiguous. Packet status, Git, timestamps, TODO order, and TODO
counts are never mapped to a current phase. These optional markers are
Inspector presentation metadata, not additions to the SDAD state schema.

### Current-source presentation limits

The working source candidate parses the complete bounded TODO preview, without
an additional item-count cutoff. Fenced examples are not executable work;
explicit deferred headings also apply to their nested sections. Missing,
truncated, failed or stale reads do not establish exact totals or zero work.
Available prefix items may still be inspected with the incomplete-read limit.

Packet status remains the original declared value. The accompanying explanation
does not execute validations, verify an external condition or confirm owner
acceptance. Doctor checks repository structure; a clean Doctor report never
stands in for the declared software checks. Incomplete, diagnostic or stale
Doctor observations must remain distinguishable from a current zero-finding
result in the UI and exported report. These are presentation fixes, not a new
snapshot, state schema or retroactive claim about released binaries.

If a rescan fails, its previous snapshot remains available as stale evidence,
with the original inspection identity, timestamp and findings. A successful
subsequent scan replaces it. The failure never creates a new successful result.

External design examples and their evidence limits are recorded in
[the dated workflow research note](WORKFLOW_RESEARCH.ko.md).

## SDAD 3.2.2 Coordination Profile

The optional **SDAD 3.x Coordination and Decision Trace Profile** remains a
document-only SDAD 3.2.2 protocol surface. When an inspected project activates
the profile, it routes these canonical documents through the existing
`sdad-state.yaml#routed_docs` list:

- `docs/sdad/playbooks/coordination-and-decision-trace.md`;
- `docs/implementation-notes.md`.

The conventional TODO and findings ledgers remain available through their
existing fixed paths. Inspector reads the routed profile and decision notes
with the same bounded, repository-contained Markdown reader used for every
other eligible document. This requires no new state schema, Doctor report
schema, Inspector snapshot schema, adapter capability, or project write.

Inspector treats lane metadata, decision origins, direct-impact references,
terminal results, reconciliation blocks, and Rule 5 lifecycle text as
human-readable repository evidence. It does not:

- allocate or validate packet, lane, decision, or finding IDs;
- infer that a dependency is satisfied or a result is integrated;
- turn a candidate into active scope or normative policy;
- infer evidence-ready, owner acceptance, release, or production readiness;
- provide locks, fencing, dispatch, scheduling, or automatic integration.

`Agent completed`, `Integrated locally`, and `Released` are coordination or
claim labels, not new `active_packet.status` values. Any future structured
projection of these documents requires a separate Inspector compatibility
packet, explicit parsing limits, no-write tests, and an independently versioned
snapshot contract. The canonical Markdown remains authoritative.

## Protocol Adapter Boundary

Inspector orchestration does not import the official SDAD engine, state reader,
document reader, or Rule 5 implementation directly. It resolves one explicit
`ProtocolAdapter` from the process-local registry and uses that adapter for:

1. engine authentication and version bounds;
2. Doctor invocation and raw report capture;
3. Doctor report normalization;
4. watched control paths and normalized state loading;
5. live evidence documents and development activity;
6. optional protocol-specific surfaces such as Rule 5 proposals.

The normalized snapshot records `protocol.adapter_id`, names, source paths,
capabilities, supported engine/report/state versions, and the canonical control
loop. The React renderer uses this metadata for visible engine and source labels;
it does not import adapter code or access the filesystem.

The built-in adapter is `official-sdad-3`. It is the only adapter shipped in the
0.0.4 portable executable and retains the exact compatibility lane documented
below. A source-mode host may install another adapter by subclassing
`sdad_inspector.protocols.ProtocolAdapter`, registering an already imported
instance, and selecting it explicitly:

```python
from sdad_inspector import inspect_project, register_protocol_adapter

adapter = MyOrganizationSdadAdapter()
register_protocol_adapter(adapter)
snapshot = inspect_project(
    project_root,
    engine_checkout,
    protocol_adapter=adapter.descriptor.adapter_id,
)
```

The equivalent CLI selector is `--protocol-adapter <adapter-id>`. Inspector has
no entry-point discovery, project-local plugin folder, state field, environment
variable, or routed-document instruction that imports adapter code. An inspected
repository therefore cannot expand execution authority. Unknown adapters and
unsupported engine versions fail closed before Doctor execution. Every new
adapter needs its own immutable engine identity, schema fixtures, no-write tests,
and bounded platform claims.

## Released Engine Identities

| Engine | Annotated tag | Peeled commit | Release contract |
| --- | --- | --- | --- |
| SDAD 3.2.1 | `v3.2.1` | `1ec10141782c33e6c2ea8be641a7ef95206f10bd` | `https://github.com/LiveTrack-X/spec-driven-ai-development/tree/v3.2.1` |
| SDAD 3.2.2 | `v3.2.2` | `cd1b1ddb3e6bcb19b531034742c7d67b4257768e` | `https://github.com/LiveTrack-X/spec-driven-ai-development/tree/v3.2.2` |
| SDAD 3.2.3 | `v3.2.3` | `707cc8861df0340b2a2bb7c9761d3529ca387684` | `https://github.com/LiveTrack-X/spec-driven-ai-development/tree/v3.2.3` |

The v3.2.3 tag is pinned to the released commit above; prior tags remain supported. The release
note declares no new state schema, report schema, Doctor check, or finding ID.
Golden data is captured from clean detached released-tag checkouts. A dirty
development tree is never a golden source.

## Version And Schema Separation

- Doctor version, state schema version, report schema version, and future
  Inspector snapshot schema are independent contracts.
- All three engines recognize state schemas 1 and 2.
- Unguarded state-v1 and unguarded missing-state reports retain report schema 1.
- A matching `--require-version` guard or effective state v2 selects report schema 2.
- Report schema 2 includes `doctor_version` and `state_version`; report schema 1 does not.
- Exit 0 means the completed diagnostic does not fail under the selected strictness.
- Exit 1 means completed findings failed the selected strictness; it is not a CLI diagnostic error.
- Exit 2 means invocation/root/version diagnostics prevented a completed project inspection.

## Compatibility Fixture Set

For each released engine the golden corpus contains:

1. exit 0, valid state v1, unguarded, report schema 1;
2. exit 0, valid state v2, matching guard, report schema 2;
3. exit 1, missing state, unguarded, report schema 1;
4. exit 2, invalid guarded invocation, report schema 2.

Machine-specific project roots are normalized to `<PROJECT_ROOT>`; no finding,
check, severity, diagnostic kind, schema field, or message is rewritten. The
manifest records the source tag, peeled commit, command shape, exit code, and
SHA-256 for every normalized file.

Recapture fixes only Doctor's date dependency to `2026-07-15`, the golden
projects' declared state date. The tagged source and CLI arguments remain
unchanged. This makes the twelve compatibility cases reproducible after their
recording date; it does not prove current state freshness. The initial 3.2.3
wall-clock capture correctly reported the old fixture state as stale.

Offline integrity is checked with `python scripts/validate_sdad_compatibility.py`. A clean
local SDAD checkout can additionally reproduce all reports from immutable tag
archives with `python scripts/validate_sdad_compatibility.py --sdad-repo <CHECKOUT> --recapture`.

Unsupported-state, version-mismatch, malformed/truncated JSON, unusual path,
and handoff relationship fixtures remain an explicitly deferred expansion for
the headless core; they are not silently claimed by this corpus.

## Snapshot Integration Decision

The compatibility corpus does not propose or depend on a new SDAD snapshot CLI. The Inspector
will invoke released Doctor JSON and combine it with separately bounded,
read-only control-file metadata in Inspector-owned snapshot schema 2. Schema 2
adds the required `protocol` descriptor while preserving raw Doctor JSON and the
actual exit code as separate evidence. Inspector snapshot schema, Doctor report
schema, state schema, adapter version lane, and product version remain
independent contracts.

## Claim Boundary And Owner Gates

Passing the compatibility corpus proves only that the recorded tagged Doctor outputs are
internally consistent with this compatibility contract on the local capture
environment. It does not prove an Inspector runtime, repository no-write
behavior, UI correctness, package behavior, or Windows/macOS/Linux support.

Release, signing, publishing, and auto-fix/write remain owner gates. Doctor
green is structural evidence only and cannot satisfy those gates or grant owner acceptance.

## Optional interaction projection (Inspector 0.0.4)

Snapshot schema 2, state v2 and released Doctor remain unchanged. The live document
response can include an optional `interactions` member with independent
`schema_version: 1`; clients ignore unknown projection versions and retain raw
Markdown browsing. The canonical authoring specification is SDAD protocol
`docs/v4/INTERACTION-REPORT-CONTRACT.md` in released SDAD v3.2.3.

Opt in existing routed Markdown with `<!-- sdad-interactions:1 -->`, then use
top-level `sdad-interaction` JSON fences (version 1). The projection only reports
explicit request, interpretation, progress, decision and correction response
records, with source path/line/content digest and observation time. User request
sources, AI reports and Inspector observation are separate. No evidence tier,
active packet status, approval or owner acceptance is automatically upgraded.

Corrections use app-owned `/api/corrections` storage, protected by the existing
loopback session/Host/Origin checks. POST requires the exact current project root;
no inspected-project writes or arbitrary destination paths are supported. Requests are sealed before clipboard exposure; `sealed` means copy success is
unconfirmed. Sealed/copied requests are immutable, and only a successful
clipboard result advances the copy state. A new correction gets a new UUID and supersedes pointer.
Draft persistence is bounded (40 records / 512 KiB UTF-8), explicit and independent of port.
The byte limit is checked before replacement. An app-side OS file lock serializes
read-modify-write across instances/processes. Optional nonnegative `revision`
(default 0 for legacy rows) enables compare-and-save; a stale edit is rejected
without overwriting stored text. Successful edits increment it; identical retries
retain revision and history position. This storage revision is separate from the
requirement's `base_revision`. Same-page navigation retains unsaved text by exact
project/packet/request; reload persistence still requires explicit Save/Copy.
A conflicted edit can be continued with a new ID. A new correction uses explicit
selection or a unique supersedes leaf, never recopy timestamp/order.

Response matching requires project, packet, request, correction ID and baseline.
An applied/verification response can explicitly link `result_revision` to the
current updated requirement; older result revisions remain stale. Competing
records are conflicts, never timestamp-selected. Source failures clear the live
projection on refresh. Verification is always labeled as reported, with bounded
evidence source actions, never as independently executed by Inspector.

The manual flow is read report -> edit correction -> preview/copy -> user delivers
to their working agent -> agent writes response to existing authority -> re-scan.
Direct transport remains outside this release. The 0.0.4 package includes this manual flow; W5 participant evaluation remains incomplete.

Plan/task disclosures consume the existing bounded documents and local TODO
parser output only. Optional presentation fields retain the TODO's summary,
continuation body and one-based source line; they do not add a wire schema or
new repository authority. Cross-project documents never populate Plan details.
No background reads, project writes, inferred hidden plan or execution signals
are introduced by detail navigation.
## Plain item correction requests

Objective and TODO correction copy is a local text-composition action, separate
from the optional exact-ID interpretation-correction protocol. It includes the
selected project/packet, source location, observed source identity, original item
and user text. It never assigns an inferred request ID to an arbitrary TODO or
claims response linkage, receipt, application, validation or project mutation.
Current readable same-project source evidence is required for copy. Drafts are
isolated by project, packet, item and source revision and retained only within
the page session. No endpoint, polling loop, state schema or write authority is added.

## Optional bounded evidence workflow

Document paging is an explicit read through the selected authenticated engine's
existing context helper. `POST /api/documents/page` binds the selected project,
current route and source SHA-256. Continuations require that digest; a changed
source preserves the displayed page and requires an explicit restart. Older
engines without the helper report unsupported capability. Files remain limited
to 1,000,000 bytes, pages to 500 lines/50,000 serialized bytes; the UI requests
100 lines. Page-local Markdown does not establish whole-document task counts.
Optional ledger completeness flags distinguish bounded counts from full totals.

`POST /api/verification-receipts` reads explicitly routed optional receipts.
The [receipt contract](VERIFICATION_RECEIPTS.md) owns recording, bounds and claim
limits. Inspector does not execute the recorded command. Recorded outcomes,
current source identity and retained log identity are separate observations;
none changes State v2, Doctor output, completion or acceptance.

`POST /api/resume-comparison` binds project and (for saving) inspection ID.
It stores only bounded metadata from completed coherent Inspector snapshots in
an app-owned SQLite database beside preferences, outside the inspected project.
Enable and baseline replacement are explicit; later successful observations
retain the baseline. The response contains the current project only. Failed,
diagnostic or stale inspections do not replace the saved observation. Metadata
includes objective/status/gates/pointers and source hashes, never document
bodies. Up to eight projects and 192 KiB of serialized observation data are
retained; SQLite allocation can exceed that logical payload limit. Clear-current
and clear-all controls are explicit. A new browser origin or port does not lose
the stored baseline. Comparisons do not reactivate work or grant permission.
