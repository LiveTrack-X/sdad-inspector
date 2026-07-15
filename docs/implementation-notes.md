# Implementation Notes

Status: Active
Scope: Current spec-unstated implementation decisions

Use this file when implementation requires a judgment the active SPEC did not
explicitly make.

Do not use this as a transcript of raw internal reasoning or a mechanical edit
log. Keep it short enough for a fresh AI session to read as current context.

## Current Notes

## IMPL-0001 - Keep snapshot assembly Inspector-owned

- Date: 2026-07-15
- Applies to: Packet `SI-001-contract-and-fixtures` and the first headless core.
- SPEC gap: The product plan required a decision on whether to propose an SDAD snapshot CLI.
- Decision: Do not add or depend on a new upstream snapshot CLI. Invoke the
  released Doctor JSON contract and assemble additional bounded, read-only
  metadata in the Inspector core under a separate snapshot schema.
- Why: Doctor is intentionally structural and released; changing it would make
  Packet 0 depend on unreleased upstream behavior and blur authority boundaries.
- Alternatives rejected: modifying Doctor output; shelling arbitrary declared commands;
  reading the whole repository into one snapshot.
- Supersedes: None.
- Verification impact: fixtures preserve raw Doctor schema differences before
  future normalization tests; the Inspector snapshot schema must version independently.
- Follow-up: Revisit only if multiple consumers prove a stable upstream need.

## IMPL-0002 - Use a fixed authenticated engine child in frozen builds

- Date: 2026-07-15
- Applies to: Packet `SI-005-native-preview`.
- SPEC gap: The SPEC required a bundled engine but did not define how an
  onedir executable should launch Doctor after `sys.executable` becomes the GUI
  application rather than a general Python interpreter.
- Decision: Source mode uses `python -I -B scripts/sdad.py`. Frozen mode routes
  only the exact bundled `sdad-engine/scripts/sdad.py` through a hidden internal
  child flag. The child authenticates the marker and whole release-tree digest,
  disables bytecode writes, and then uses `runpy` with the original Doctor
  arguments. External engine paths are rejected in frozen mode.
- Why: This preserves process isolation and real exit/stdout evidence without
  bundling a second arbitrary Python interpreter or exposing general script
  execution through the desktop executable.
- Alternatives rejected: reuse the GUI executable with Python `-I` arguments;
  import Doctor into the GUI process; accept arbitrary script paths; ship an
  independently managed runtime interpreter.
- Verification impact: frozen command routing has a regression test; the built
  Windows artifact must complete the bounded launch smoke after every change.
- Follow-up: Keep the internal flag undocumented as a user command and fixed to
  the authenticated bundled path.

## Routing

- If the note creates future work, update `docs/TODO-Open-Items.md`.
- If the note records a bug, risk, or blocked issue, update `review-findings.md`.
- If the note is durable architecture, policy, release, security,
  data-boundary, or owner-approved tradeoff rationale, create or update an ADR.
  A decision normally deserves an ADR only when it is hard to reverse, would
  surprise a future maintainer without context, and represents a real tradeoff.
- New durable notes use a never-reused `IMPL-NNNN` ID. Existing unnumbered notes
  remain valid. Date is descriptive; identity and supersession use the note ID.
- At packet boundaries, classify each note by current effect rather than age:
  keep current small constraints here; promote requirements to SPEC, durable
  rationale to ADR, work to TODO, and defects/risks to findings.
- When a note is promoted or superseded, leave only a pointer to the new
  authority. Do not keep two mutable copies of the same decision.
- If current notes exceed a bounded read or mix unrelated domains, split by
  topic and keep this file as the small current router. Archive only decisions
  that no longer affect current work, verify inbound links, and never route all
  archive files at startup.
