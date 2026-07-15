# Localization Contract

Status: Active implementation contract
Packets: `SI-006-korean-localization`, `SI-008-context-workspace-progress-theme`

## Supported interface languages

The shared React frontend supports Korean (`ko`) and English (`en`). This is the
same bundle served by the loopback browser app and embedded by the optional
native shell.

Locale selection is deterministic:

1. A valid value in `sdad-inspector:locale:v1` wins.
2. Otherwise, a primary browser language beginning with `ko` selects Korean.
3. Every other or unavailable browser language selects English.

The command-bar selector changes the locale immediately, persists only the
locale token, and updates `html[lang]`. Storage failures do not block the active
session from changing language.

## Translation boundary

Product-owned navigation, labels, loading/error states, accessibility names,
safe-action descriptions, and live announcements are localized. Repository and
engine evidence remains verbatim, including:

- packet IDs, status tokens, paths, commands, and relationship tokens;
- owner-authored objectives and validation descriptions;
- Doctor finding messages and remediations;
- raw snapshot JSON and timestamps.

No translation service, network request, project write, or backend mutation is
used. The locale preference is browser-local product UI state, not inspected
repository state.

## Theme preference

The shared frontend supports `light` and `dark`. A valid value in
`sdad-inspector:theme:v1` wins; otherwise the first load follows
`prefers-color-scheme`. The localized command-bar control changes the theme
immediately and persists only the theme token. It updates `html[data-theme]`
and `color-scheme`, never repository state. Storage failures may discard the
preference but must not prevent the active session from switching theme.

## Adding another locale

Add the locale token and a complete typed catalog in `web/src/i18n.tsx`, extend
locale detection and the explicit selector, then add interaction tests for
detection, switching, persistence, `html[lang]`, and verbatim evidence. A
missing catalog key must remain a TypeScript error.

## Validation

Run from the repository root:

```powershell
npm --prefix web run typecheck
npm --prefix web test -- --run
npm --prefix web run build
python scripts/validate_browser_contract.py
```

Rendered QA must cover Korean at desktop width, explicit English switching,
reload persistence, and the narrow layout. Native claims require a rebuilt
artifact and its own bounded smoke; browser evidence alone is not native or
cross-platform evidence.
