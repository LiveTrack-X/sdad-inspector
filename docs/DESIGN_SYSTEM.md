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
- `DevelopmentFlow`: exact `Plan → Route → Implement → Verify → Report` rail,
  conditional Gate/Handoff cards, neutral evidence states, an active-packet
  summary, explicit-only current TODO/phase emphasis, openable bounded evidence
  documents, and a secondary worktree evidence lens. Current emphasis uses the
  cobalt focus treatment and never reuses the green verified treatment.
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
