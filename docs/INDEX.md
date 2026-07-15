# Project Documentation Router

Status: Active

## First Read

1. Read `../sdad-state.yaml` for scale, packet, gates, checks, and routes.
2. Read this table.
3. Inspect current source/tests/runtime.
4. Let intent select one eligible path, heading, section, or match; membership
   is not a read-all instruction.

Do not load full rules/history/evidence by default.

## Working Route

| Intent or trigger | Read now | Load on demand |
| --- | --- | --- |
| Any active packet | state, source/tests | intent-selected route |
| Implement or fix | active SPEC, `TODO-Open-Items.md`, `../review-findings.md` | implementation notes; ADR for durable tradeoff |
| New/additional/conflicting SPEC | current owner request, state `active_spec`, source/tests | supplied/discovered SPEC; work-packets playbook |
| Review or audit | source/tests, active SPEC, active findings | relevant operating-rule heading |
| Docs or behavior change | affected docs and active SPEC | documentation-and-handoff playbook |
| Protected action/owner decision | active SPEC, gates, decision record, intersecting deferred findings | risk/version policy; readiness |
| Product, hardware, compatibility, package, remote, or public claim | `evidence-matrix.md`, `claim-registry.md` | artifact contract, packet state, remote import |
| Pause/resume/handoff; blocked/deferred; late result | state; current handoff; packet TODO/finding/gate | work/evidence playbook |
| Historical or reference intake | current code/docs/SPEC first | product notes, external reference, then archive |

## On-Demand Policy And Playbooks

- authority/code policy: `Repository-Operating-Rules.md` by heading;
- large/private input: `sdad/playbooks/context-and-data.md`;
- scale/scope/packet/delegation: `sdad/playbooks/work-packets.md`;
- owner gate, claim, parity, or release: `sdad/playbooks/evidence-and-risk-gates.md`;
- docs/state/handoff: `sdad/playbooks/documentation-and-handoff.md`;
- adaptive-rule portability or harness/eval/memory loops:
  `sdad/playbooks/advanced-extensions.md`.

## Write Route

| New information | Record in |
| --- | --- |
| Scope, behavior, non-goal, acceptance criterion | active SPEC |
| Current task or deferred work | `TODO-Open-Items.md` |
| Defect, blocked check, unresolved risk | `../review-findings.md` |
| Spec-unstated implementation choice | `implementation-notes.md` |
| Hard-to-reverse surprising tradeoff | numbered ADR under `../SPEC/adr/` |
| Evidence/claim status | evidence/claim ledger |
| Owner authorization/result acceptance | project-chosen durable decision path/URL/ID; link elsewhere |
| Current execution declaration | `../sdad-state.yaml` |
| Cross-session recovery pointers/results | state-declared current handoff |

## Source Of Truth

Source/tests/runtime establish observed behavior. The state-declared active SPEC
establishes intended scope and acceptance criteria; another SPEC controls only
incorporated scope. State owns execution; handoff owns continuity. A current
applicable owner instruction can interrupt or redirect work immediately and is
persisted before affected stateful implementation. References, archives, names,
dates, and old/provider-retained chat memory cannot activate scope. Record owner
decisions in their authoritative home.

## Active Catalog

- Core: state, installed tool adapter, state-declared active SPEC (default
  `../SPEC/SPEC-COMPLETE.md`), `TODO-Open-Items.md`,
  `../review-findings.md`, `implementation-notes.md`.
- Policy: `Repository-Operating-Rules.md`.
- Procedures: `sdad/playbooks/` (load one triggered file only).
- Optional: `evidence-matrix.md`, `claim-registry.md`, artifact, readiness, and
  remote-import records.
- Current handoff: use `../sdad-state.yaml#current_handoff` when declared.
- Native preview: `CROSS_PLATFORM.md` for build/runtime adapters and platform
  claim limits.
- Localization: `LOCALIZATION.md` for Korean/English selection, persistence,
  and the verbatim repository-evidence boundary.
- Future update/migration: `UPDATE_AND_MIGRATION.md` for independent Inspector
  and engine versions, authenticated release caching, preview, owner-gated
  apply, verification, and rollback.
- Current alpha release: `releases/v0.0.1-alpha.3.md` for assets, compatibility,
  usage, and unsigned limitations.
- Continuity templates: `sdad/handoffs/`.
- Decisions: `../SPEC/adr/`.

## Maintenance

Keep this routing-only. Keep state, TODO, findings, and current handoff short;
archive closed history. At handoff, report docs changed/checked and checks run.
