# Localization And Display Preferences

Status: Active implementation contract

Packets: `SI-006-korean-localization`, `SI-008-context-workspace-progress-theme`,
`SI-018-post-update-and-usability-hardening`

## Supported interface languages

The shared React frontend supports English (`en`), Korean (`ko`), Japanese
(`ja`), and Simplified Chinese (`zh-CN`). The loopback browser app and optional
native shell use the same bundle. English is the source catalog and the safe
fallback. All four typed catalogs cover every current product-owned label, so
adding a new label without extending every catalog fails frontend type-checking.

First-use locale selection is deterministic:

1. A valid Inspector-owned preference injected into `meta[name="sdad-locale"]`
   wins. This preserves an explicit choice across changing loopback ports.
2. Otherwise, a valid value in browser storage key
   `sdad-inspector:locale:v1` is used as an origin-local fallback.
3. Otherwise, the first supported computer/browser locale in
   `navigator.languages` selects `ko`, `ja`, `zh-CN`, or `en`.
4. Unsupported or unavailable locales fall back to English.

The command-bar selector changes the locale immediately, updates `html[lang]`,
and posts the preference to the authenticated loopback service. Preference
write or browser-storage failures do not block the active session.

## Translation boundary

Product-owned navigation, labels, loading/error states, accessibility names,
safe-action descriptions, update messages, and live announcements are
localized. Repository and engine evidence always remains verbatim, including:

- packet IDs, status tokens, paths, commands, and relationship tokens;
- owner-authored objectives and validation descriptions;
- Doctor finding messages and remediations;
- raw snapshot JSON, YAML, Markdown, and timestamps.

No translation service or network request is used. Locale selection mutates
only Inspector-owned user preferences and never writes the inspected
repository. The language-specific public guides are `README.md`,
`README.ko.md`, `README.ja.md`, and `README.zh-CN.md`.

## Theme preference

The frontend supports `light` and `dark`. A valid Inspector-owned preference
injected through `meta[name="sdad-theme"]` wins across native launches. The
origin-local `sdad-inspector:theme:v1` value is a fallback; first use otherwise
follows `prefers-color-scheme`.

The command-bar control changes the theme immediately, updates
`html[data-theme]` and `color-scheme`, and persists the choice through the
authenticated preference endpoint. Failure to persist never prevents the
current session from changing theme.

## UI scale preference

The default UI scale is 110%. Users can select 90%, 100%, 110%, 120%, 130%,
140%, or 150% through the product controls. `Ctrl/Cmd` + `+` or `-` changes one
step and `Ctrl/Cmd` + `0` restores 110%. A valid Inspector-owned value injected
through `meta[name="sdad-ui-scale"]` wins; browser key
`sdad-inspector:ui-scale:v1` is the fallback.

Scaling changes only the rendered product UI. It does not change evidence,
snapshots, source files, or any inspected-project content.

## Preference storage boundary

Theme, locale, UI scale, and recent projects share the bounded, versioned
Inspector preference document in per-user application data:

- Windows: `%LOCALAPPDATA%\SDAD Inspector\preferences.json`
- macOS: `~/Library/Application Support/SDAD Inspector/preferences.json`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/sdad-inspector/preferences.json`

The server accepts only enumerated theme/locale values and scale steps, limits
the file to 64 KiB, and writes it atomically. Clearing recent-project history
preserves display preferences. Project selection updates no file inside the
selected repository.

## Adding another locale

Add the locale token and catalog in `web/src/i18n.tsx`, extend detection and
the selector, add a language-specific README when the locale is public, then
add interaction tests for detection, explicit switching, native preference
precedence, `html[lang]`, persistence, and verbatim evidence.

## Validation

Run from the repository root:

```powershell
npm --prefix web run typecheck
npm --prefix web test -- --run
npm --prefix web run build
python -m unittest discover -s tests -v
python scripts/validate_browser_contract.py --sdad-checkout .runtime/sdad-v3.2.2
```

Rendered QA covers all four locale choices, theme and scale restoration,
desktop and narrow layouts, and the first-launch chooser. Native or
cross-platform claims require rebuilt artifacts and their bounded smoke checks;
browser evidence alone is not native or cross-platform evidence.
