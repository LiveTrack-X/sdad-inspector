# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

## Durable Product Decision

The owner selected concept 3, Split Inspector, on 2026-07-15. Match
`../design/reference/sdad-inspector-split-inspector.png` and the interaction
contract in `../docs/DESIGN_REFERENCE.md`. Do not substitute a dashboard/card
layout or a different icon family. Production UI data must come from the local
snapshot API; fixture data is test-only.

The owner also requires quick project switching in the existing project modal:
system folder selection, explicit paste, current/recent projects, and a clear
history action. Active SPEC and TODO selections render their live Markdown in
the central workspace; eligible routed document rows and left-tree items open
the same safe Markdown reader. Development monitoring follows the supplied dense dark
progress-board reference but must remain inside the Split Inspector center pane
and distinguish observed Git worktree/commit metadata, packet-tagged TODO work,
and repository handoff history from declared SDAD facts. Show source timestamps
without guessing work times or causal packet attribution; never fabricate a
score, percentage, commit, agent activity, or work-loop phase. Re-scan remains
manual by default; explicit `AUTO 15s` shows a countdown, pauses while hidden,
resets after manual/project scans, and never overlaps another scan.

All automatic workspace evidence refresh is governed by that one visible AUTO
15-second control. Initial load, manual scan, AUTO scan, and project switch update
snapshot, live Markdown, and development activity as one stable cycle; do not
add independent background document/activity polling. Preserve the selected
Markdown document, its scroll position, and panel geometry across refreshes.
Overview file-like relationship paths are controls that open the same central
reader. Active-packet TODO counts share one parser everywhere. Human-readable
localized Git labels lead; raw porcelain is secondary detail. The five-stage
Scope/Build/Verify/Evidence/Docs-Handoff board classifies observed/declared
signals and must never imply execution, passage, causality, or completion.
Recent projects use the engine's bounded per-user app preference store because a
native loopback port can change between launches. Keep Clear history visible in
the project dialog and disabled only when there is no history; neither action may
write to an inspected repository.
Rule 5 extraction shows candidate provenance and every lifecycle field. Saving
requires a fresh digest-matched viewer preview and explicit checked confirmation,
then uses a cancellable Save As dialog for one local Markdown proposal. Never
present a proposal as an active rule, write the inspected repository, or modify
authority/validators automatically.

Preserve the selected three-pane layout while increasing baseline typography,
line height, contrast, and click/touch targets. Give the center Markdown and
timeline workspace the dominant reading width on desktop and a readable single-
pane surface at narrow widths. Keep Overview as the first left-tree destination;
desktop pane dividers are bounded pointer/keyboard-resizable and locally
persistent, while narrow layouts use the established drawer behavior.
