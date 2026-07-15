# Split Inspector UI System

Status: Active implementation inventory

## Layout

- Command bar: 56 px high.
- Workspace: three panes at desktop widths; repository 31%, overview 38%,
  inspector 31%, each separated by a 1 px cool-gray rule.
- Provenance bar: 36 px high and pinned to the viewport bottom.
- Below 1080 px the Inspector becomes a drawer/tab surface. Below 720 px the
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

- `CommandBar`: app identity, current root, engine version, re-scan, reveal,
  copy, overflow. Re-scan exposes busy state and result announcement.
- `RepositoryTree`: filter input, expandable groups, selection, counts, status
  text, keyboard arrow navigation, empty-filter message.
- `Overview`: active packet/status, objective, Doctor summary, relationships,
  and validation declarations with a persistent not-executed notice.
- `InspectorPane`: Inspector/Raw JSON tabs, selected field provenance, owner
  gates, safe actions, copy feedback.
- `StatusBar`: Doctor/report/state versions, exit code, inspected time, lock.
- `ProjectDialog`: canonical path input and explicit open action.
- `StateSurface`: loading, unsupported/error, stale, no state, and retry.

Phosphor is the only UI icon family. State never relies on color alone. All
interactive elements expose a visible focus indicator and accessible name.
