# Split Inspector UI System

Status: Active implementation inventory

## Layout

- Command bar: 58 px base height, with the generated 27 px product logo.
- Workspace: three panes at desktop widths; repository 31%, overview 38%,
  inspector 31%, each separated by a 1 px cool-gray rule.
- Provenance bar: 36 px high and pinned to the viewport bottom.
- Below 1180 px the Inspector becomes a drawer/tab surface. Below 760 px the
  repository becomes a dismissible navigation panel and the Overview remains
  primary.

## Tokens

| Role | Value |
| --- | --- |
| canvas | `#f7f9fc` |
| surface | `#ffffff` |
| subtle surface | `#f2f5f9` |
| ink | `#10213f` |
| secondary ink | `#526176` |
| divider | `#d8dee8` |
| cobalt | `#0b64d8` |
| cobalt wash | `#eaf3ff` |
| verified | `#24893e` |
| stopped | `#b86400` |
| error | `#d21f2b` |
| focus ring | `0 0 0 3px rgba(11, 100, 216, .25)` |

Typography uses `Inter`, `Segoe UI`, system sans-serif fallbacks. Paths, packet
IDs, commands, and JSON use `"SFMono-Regular", Consolas, monospace`. The base
size is 14 px, compact labels are 12 px, and the active packet title is 22 px.

## Components And States

- `CommandBar`: app identity, current root, adapter-supplied engine label,
  re-scan, reveal, copy, overflow, and an explicit product-update check. The
  path and engine label are shrink-safe and secondary action labels collapse
  before they can overlap. Re-scan exposes busy state and result announcement.
- `UpdateNotice`: compact checking/downloading/progress/ready/countdown/apply/
  success/error states. The verified-ready state defaults to automatic restart
  but keeps Update now and Later controls visible.
- `RepositoryTree`: filter input, expandable groups, selection, counts, status
  text, keyboard arrow navigation, empty-filter message. Full label/value text
  remains available through titles; at a resized pane width of 310 px or less,
  values move below labels instead of colliding.
- `Overview`: active packet/status, objective, Doctor summary, relationships,
  and validation declarations with a persistent not-executed notice. It starts
  directly with repository evidence and does not render README marketing art.
- `DevelopmentFlow`: a compact exact `Plan → Route → Implement → Verify →
  Report` orientation rail followed by one plain-language current-situation
  statement and a four-row Now / Reason / Caution / Next Check evidence stack.
  Each reasoning row opens its bounded source and distinguishes declared,
  observed, structurally verified, and unknown facts. The rail is never a
  progress meter: only an explicit matching open TODO with `[current]` and one
  consistent `[phase:...]` marker receives the cobalt current treatment.
  Active packet/current TODO, bounded evidence documents, conditional
  Gate/Handoff branches, and the secondary worktree lens remain available below
  the primary explanation. Green remains reserved for verified evidence.
- `DocumentViewer`: bounded Markdown content, routed-document navigation, safe
  image fallbacks, and no HTML/script or automatic remote-image execution.
- `EvidenceView`: provenance metadata followed by the same bounded evidence
  body. In-memory Doctor/snapshot evidence uses scrollable JSON, state uses
  verbatim YAML, and Markdown reuses `DocumentViewer` rendering safety.
- `InspectorPane`: Inspector/Raw JSON tabs, selected field provenance, owner
  gates, safe actions, copy feedback. Long owner-gate names and unobserved
  status text use two explicit rows so neither column can overlap the other.
- `StatusBar`: Doctor/report/state versions, exit code, inspected time, lock.
- `ProjectDialog`: canonical path input and explicit open action.
- `StateSurface`: loading, unsupported/error, stale, no state, and retry.

Phosphor is the UI control icon family; the generated logo is an app brand asset
and the one-line banner is a README-only introduction asset. Neither is a
control icon. State never relies on color alone. All
interactive elements expose a visible focus indicator and accessible name.

## SI-021 request and correction surface

DevelopmentFlow retains the Split Inspector layout and adds the request selector,
attributed request, explicit interpretation and requirement/decision reports above
the stage situation summary. Correction drafts use native labeled fields, a
reviewable text preview and explicit save/copy actions. Copied requests remain
read-only and can be superseded by a new correction. History displays transport
and AI-report stages without green verification or acceptance styling. Existing
surface/divider/ink tokens cover both themes; controls wrap at narrow widths.

## Plan and task detail access

The packet TODO separates current markers, other open entries, checked entries,
and explicitly deferred work. Open entries keep source order without selecting
an execution priority. Known packet deferral still groups preserved open entries
as deferred when the TODO observation is incomplete; counts remain unknown.
The original task text, detail and source access remain unchanged.

Verification comparisons retain two explicitly inspected observations with
separate timestamps and limits. The responsive table keeps field labels and
original evidence access available at narrow widths. A missing resume baseline
is explained only after a successful read for the current project and inspection;
loading and errors never imply absence or trigger a baseline save.

The Plan label is a keyboard-operable disclosure in the existing orientation
rail. It opens a center-pane section with the declared objective, explicitly
Plan-tagged work and bounded connected documents. Source previews use the same
Markdown renderer and open the full central reader on request. The selected
detail does not change `aria-current`, evidence status or execution meaning.
TODO summaries expand inline to reveal continuation/child lines, declared
status/stage, source section and line. The remaining-work heading opens the full
TODO from both Overview and Development Flow. Native disclosures retain visible
focus and use the existing light/dark tokens and narrow-width wrapping.
# Request review entry and item corrections

Overview begins with the current request and AI interpretation, using the same
report component and refresh cycle as Development Flow. The paired reports use
two columns where space permits and stack on narrow screens. Existing source,
uncertainty and correction-response meanings remain unchanged.

Declared objectives and expanded TODO items offer a compact correction disclosure.
It previews the exact selected source/item and editable user request before copy.
Keep missing/stale sources disabled and state that copy does not confirm delivery.
Preserve input across workspace navigation; reload is the page-session boundary.
