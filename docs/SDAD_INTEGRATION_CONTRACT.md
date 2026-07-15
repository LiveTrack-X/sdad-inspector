# SDAD Integration Contract

Status: Active
Observed: 2026-07-15

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
0.0.1 portable executable and retains the exact compatibility lane documented
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

The v3.2.2 tag peels to the same commit observed at `origin/main`. The release
note declares no new state schema, report schema, Doctor check, or finding ID.
Golden data is captured from clean detached released-tag checkouts. A dirty
development tree is never a golden source.

## Version And Schema Separation

- Doctor version, state schema version, report schema version, and future
  Inspector snapshot schema are independent contracts.
- Both engines recognize state schemas 1 and 2.
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
