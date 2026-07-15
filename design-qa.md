# Split Inspector Design QA

Status: PASS
Reviewed: 2026-07-15
Viewport: `1440 x 1024`

## Comparison inputs

- Owner-selected reference:
  `design/reference/sdad-inspector-split-inspector.png`
- Final implementation capture:
  `design/qa/browser-mvp-final-1440x1024.png`

The reference and final implementation were opened together at original detail,
then the implementation was corrected to select the active packet so the tree,
overview, and Inspector all represented the same state before the second
side-by-side comparison.

## Fidelity ledger

| Area | Result | Evidence |
| --- | --- | --- |
| Three-pane anatomy | PASS | Repository, Overview, and Inspector retain the selected proportions, thin dividers, fixed command bar, and provenance footer. |
| Visual language | PASS | White/cool-gray surfaces, navy text, cobalt focus/selection, green verified state, amber stopped gates, and no gradients match the reference. |
| Typography and density | PASS | Sans-serif hierarchy and monospace evidence fields preserve the dense inspector character without clipped labels or overlapping controls. |
| State and provenance | PASS | Active packet, software-verified status, Doctor 0/0, relationships, stopped owner gates, and read-only provenance are all visible and mutually consistent. |
| Core interactions | PASS | Re-scan, filter, selection, raw JSON, copy path, safe reveal, project dialog, desktop layout, and narrow drawers were exercised; eleven Vitest interactions and the browser contract pass. |

## Korean and English localization QA

| Area | Result | Evidence |
| --- | --- | --- |
| Korean priority | PASS | A Korean primary browser locale selects `ko`; product navigation, controls, accessibility names, loading/error states, and announcements use the typed Korean catalog. |
| Explicit switching | PASS | The command-bar selector changed Korean to English, updated `html[lang]`, survived reload through `sdad-inspector:locale:v1`, and switched back to Korean. |
| Evidence fidelity | PASS | Packet IDs, status/relationship tokens, paths, commands, owner objectives, Doctor messages, timestamps, and Raw JSON remained verbatim in both languages. |
| Responsive behavior | PASS | `1440 x 1024` preserved the three-pane layout; `720 x 900` kept the language selector visible with document and body width exactly 720 pixels and no horizontal overflow. |
| Runtime health | PASS | Browser console errors were zero; the production bundle passed the loopback/no-write contract and the rebuilt Windows native smoke exited 0. |

## Context workspace, progress, and theme QA

| Area | Result | Evidence |
| --- | --- | --- |
| Central navigation | PASS | State, Active SPEC, TODO, findings parent/severities, handoff, evidence parent/items, and active packet selections render matching typed center views and synchronized right Inspector details; Overview restores the packet summary. |
| Observed progress | PASS | Re-scan exposed the actual Doctor stage and `scripts/sdad.py`; the authenticated progress contract sampled live execution and then the report stage, bounds history to eight events, and contains no synthetic percentage or inferred repository SDAD work-loop phase. |
| Light and dark | PASS | OS preference is used only without a saved choice; the command-bar toggle persists `sdad-inspector:theme:v1`, updates the document theme, and survives reload in Korean chrome. |
| Responsive behavior | PASS | Light and dark desktop rendering retained the three-pane reference anatomy; at `720 x 900`, repository and Inspector drawers remain usable and tree selection returns focus to the central document. |
| Runtime health | PASS | The final production bundle logged zero browser errors or warnings, passed typecheck, eleven interactions, the hardened browser contract, byte-identical native packaging, and bounded native smoke exit 0. |

## Missing-state regression QA

| Area | Result | Evidence |
| --- | --- | --- |
| Reproduction | PASS | The reported project returned `state.current_handoff: null`; the old bundle produced an empty DOM and `Cannot read properties of null (reading 'declared')`. |
| Browser fix | PASS | The rebuilt bundle rendered the Korean missing-state surface, preserved the Doctor finding, selected `현재 인계 없음`, updated Inspector detail authority to `sdad-state.yaml#current_handoff`, and logged zero errors or warnings. |
| Native fix | PASS | The rebuilt unsigned EXE launched without a path argument, selected the same project through the native folder picker, visibly exposed `Doctor 요약`, `state.missing`, and `현재 인계 없음`, and passed bounded smoke. |

## Intentional data-driven differences

- The localization captures show the real `SI-006-korean-localization` repository rather
  than the fictional payment-service data in the visual reference.
- Eight declared validation commands require central-pane scrolling at this
  viewport; no content is cropped or lost.
- No current handoff exists, so the handoff row truthfully displays `None`.

## Additional rendered evidence

- `design/qa/browser-mvp-1440x1024-pass2.png`
- `design/qa/browser-mvp-720x900.png`
- `design/qa/browser-mvp-720x900-repository.png`
- `design/qa/localization-ko-1440x1024.png`
- `design/qa/localization-en-1440x1024.png`
- `design/qa/localization-ko-720x900.png`

No release, signing, publishing, installer, or macOS/Linux visual claim is made
by this QA result.

## SI-009 live project workspace QA

| Area | Result | Evidence |
| --- | --- | --- |
| Reference fidelity | PASS | `design/qa/si009-reference-comparison.png` places the owner-selected Split Inspector reference and the final Korean dark-mode overview in one comparison. The three-pane anatomy, compact command bar, blue selection, bounded center workspace, evidence-oriented right Inspector, and provenance footer remain intact. |
| Overview progression | PASS | `design/qa/si009-overview-1280x720.png` presents the active packet first, then the packet-tagged open/completed checklist, observed worktree files, Git history, and handoff history. Empty Git/handoff states remain explicit. |
| Live document journey | PASS | Active SPEC, TODO, and an eligible routed document were selected from the repository tree and rendered as readable Markdown with source path and read time; the routed list opened the same reader rather than raw JSON. |
| Development monitoring | PASS | The Development Flow showed declared scope, bounded observed worktree paths, current packet TODO counts, declared-but-not-executed validation, and recorded Git/handoff history as distinct evidence sources with no inferred Plan/Route/Implement/Verify/Report claim. |
| Controls and layout | PASS | Manual is the default, AUTO is explicitly selectable at 15 seconds with non-overlap covered by interaction tests, labels do not wrap at 1280 px, and three desktop panes expose persisted pointer/keyboard resizing with readable reset defaults and narrow-screen drawers. |
| Runtime and package evidence | PASS | 55 Python tests (one environment-limited symlink skip), 21 frontend interactions, typecheck/build, browser/static/native contracts, strict SDAD 3.2.2 Doctor 0/0, byte-identical source/bundled web trees, and the rebuilt unsigned Windows preview smoke exit 0 passed. |

The rendered state uses real uncommitted repository data, so the worktree count
is high and recent Git/handoff sections are honestly empty. It does not assert
that the active packet caused a changed path, identify authors, or invent work
start/completion times. Owner acceptance, release, signing, publishing,
auto-fix/write, and macOS/Linux execution remain outside this QA result.

## SI-010 consistent live flow and Rule 5 QA

| Area | Result | Evidence |
| --- | --- | --- |
| Reference fidelity | PASS | A local combined comparison placed the owner-provided development-board reference and the final Inspector screen together. Inspector retains the selected Split Inspector anatomy while presenting all five evidence stages, a visible current-observation source, owner gates, larger Korean text, and readable dark-mode contrast. |
| Stable coherent refresh | PASS | Manual mode issued no auxiliary polling after the initial load. AUTO issued one non-overlapping snapshot/document/activity/Rule-5 cycle per 15 seconds. A regression interaction preserved the selected Active SPEC reader and its scroll position across a re-scan; the in-browser re-scan retained the same selected document and heading without blanking the workspace. |
| One packet checklist | PASS | One parser supplies the active-packet entries used by the repository count, Overview checklist, Development Flow, and Inspector selection. A deliberately different Doctor ledger count cannot change those visible packet totals, and source sections remain available when tagged entries span headings. |
| Navigation and Git language | PASS | Overview Active SPEC and eligible relationships opened the central safe Markdown reader by pointer. Raw `??` remains available only in detail while the visible Korean badge says `새 파일`; corresponding localized labels cover the remaining porcelain states. |
| Five-stage monitoring | PASS | The final rendered journey shows Scope, Build, Verify, Evidence, and Docs/Handoff with deterministic path/source bases. Only the newest timestamped changed file can mark `current observation`; no stage is described as run, passed, completed, or caused by the packet. |
| Rule 5 proposal journey | PASS | The final rendered Rule 5 journey shows a complete active finding selected, its generated Markdown in the central viewer, the exact SHA-256, and Save disabled until the exact-preview confirmation. Unit/HTTP/UI evidence covers incomplete candidates, stale source, digest mismatch, cancellation, exact saved bytes, extension normalization, atomic output, and inspected-repository rejection. |
| Recent project journey | PASS | Two real local projects were switched through the dialog; the prior successful project immediately appeared in the bounded recent list and remained after returning. Clear history stayed visible, with the disabled empty state covered by interaction tests. |
| Runtime and package evidence | PASS | 63 Python tests passed with one environment-limited symlink skip; 34 frontend interactions, typecheck, production build, browser/native contracts, authenticated SDAD v3.2.2 staging, and a rebuilt unsigned Windows one-folder preview smoke exit 0 passed. Browser console warnings/errors were zero during the final rendered journey. |

The Rule 5 output is proposal-only. Its system Save As destination must be
outside the inspected repository; cancellation writes no file, and saving does
not adopt, activate, enforce, commit, or publish a rule. The responsive 1280 px
capture uses a compact multi-row stage rail; wider desktop layouts place the
same five stages in one row. No owner acceptance, release, signing, publishing,
macOS/Linux execution, or automatic project-write claim is made here.

## SI-011 reader navigation and flow drilldown QA

| Area | Result | Evidence |
| --- | --- | --- |
| Reference fidelity | PASS | The owner-selected `design/reference/sdad-inspector-split-inspector.png` and final 1440x1024 screens were inspected together. The final UI keeps the three-pane Split Inspector anatomy, dominant center evidence reader, compact command bar, dark token palette, outlined cards, Phosphor icon family, source-language evidence, read-only footer, and stopped owner gates. |
| Markdown reading | PASS | The final 1440x1024 rendered screen shows the compact sticky outline. Selecting `Active Scope` focused the exact safe-rendered `H2` with deterministic ID `_r_0_-heading-144`; no repository HTML is interpreted. |
| Routed-document disclosure | PASS | Desktop exposes the eight-route disclosure open, while the final 720x900 rendered screen shows it collapsed with count and expanded-state control before the document outline. |
| Development Flow drilldown | PASS | The final 1440x1024 rendered screen shows the pressed Build stage. Browser interaction reported 66/125 changed paths, exposed an explicit all-path reset, and restored the full unchanged classification set. |
| Narrow controls and accessibility | PASS | At 720x900 the Manual/AUTO letters are replaced by HandPalm/Timer icons. Rendered accessibility inspection exposes Korean names `수동`, `자동 15초`, and `다시 검사`; regression tests pin explicit localized `aria-label` values. No clipped core control was observed. |
| Git evidence truth | PASS | A full-suite failure exposed the probe overriding system `core.autocrlf`. The minimal fix preserves effective system configuration while retaining fixed commands, `shell=False`, optional-lock/fsmonitor/untracked-cache disabling, time/output limits, and no content reads. A deterministic CRLF/system-config integration test proves a committed repository stays clean and a Unicode rename remains visible. |
| Runtime and package evidence | PASS | 63 Python tests passed with one environment-limited symlink skip; 36 frontend interactions, typecheck/build, browser/native contracts, strict Doctor 3.2.2 at 0/0, and browser console warnings/errors 0 passed. The isolated unsigned Windows preview has 1,311 files / 41,944,111 bytes, EXE SHA-256 `00710fa4c63b92612e53c890f9319896a14f194a929b9ea41e5f54bc750d2a01`, `NotSigned`, and bounded smoke exit 0. The owner-open default preview was not terminated. |

The above-the-fold product copy and evidence labels remain repository-derived;
only the new localized navigation/filter affordances were added. The selected
reference is light while the current owner-selected product state is dark, and
the current repository has more controls/data than the reference fixture; these
are intentional state-driven differences, not a new visual direction. Owner
acceptance, release, signing, publishing, auto-fix/write, and macOS/Linux
execution remain outside this QA result.

final result: passed
