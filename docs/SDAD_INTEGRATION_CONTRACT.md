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
read-only control-file metadata in an Inspector-owned snapshot schema. It must
preserve raw Doctor JSON and actual exit code as separate evidence.

## Claim Boundary And Owner Gates

Passing the compatibility corpus proves only that the recorded tagged Doctor outputs are
internally consistent with this compatibility contract on the local capture
environment. It does not prove an Inspector runtime, repository no-write
behavior, UI correctness, package behavior, or Windows/macOS/Linux support.

Release, signing, publishing, and auto-fix/write remain owner gates. Doctor
green is structural evidence only and cannot satisfy those gates or grant owner acceptance.
