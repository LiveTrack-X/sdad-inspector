# SDAD Inspector Design Reference

Status: Owner-selected visual target
Selected: 2026-07-15
Applies to: Browser MVP and native preview packets

## Selected Direction

The owner selected concept 3, **Split Inspector**. The immutable visual source
for implementation comparison is:

`../design/reference/sdad-inspector-split-inspector.png`

SHA-256:
`7f92fa69e517eca70428422720d50f11647104a6a1440ef53eb017f88c077adf`

## Required Anatomy

- A compact top command bar with product identity, inspected project path,
  engine version, re-scan, reveal, and copy-path actions.
- A left repository/control tree with filter, active state, SPEC, packet, TODO,
  findings, handoff, and evidence branches.
- A central Overview surface for active packet, Doctor summary, relationships,
  and declared validation commands.
- A right Inspector / Raw JSON detail pane with authority, observed value,
  source, freshness, finding/remediation context, stopped owner gates, and only
  safe read-only actions.
- A bottom provenance bar for Doctor version, report/state schema, exit code,
  inspection time, and read-only status.

## Visual System

- White and cool-gray surfaces with thin separators; no gradients or decorative
  dashboard cards.
- Navy text, cobalt selection/focus, green verified state, and amber stopped
  owner gates. Color is always paired with text and an icon.
- Dense desktop-first inspection layout, readable sans-serif body copy, and
  monospace only for paths, IDs, commands, and raw evidence.
- Phosphor outline icons are the implementation icon family.

## Interaction Contract

Re-scan refreshes the same project without writing it. Filtering and tree
selection update the center and right panes. Raw JSON is selectable and
copyable but never interpreted as HTML. Validation commands are presented,
never executed. Reveal and copy actions operate only on canonical paths within
the selected project root. Narrow layouts collapse the right pane first and
retain keyboard access to every control.

Owner-directed packet `SI-008-context-workspace-progress-theme` extends this
contract without replacing the immutable visual source: the center uses a real
Overview return tab plus a selection-specific tab; running scans show only
service-emitted Inspector pipeline stages and current bounded sources; and the
same semantic visual system supports a locally persisted dark theme. No scan UI
may claim the inspected repository's SDAD work-loop phase without evidence.
