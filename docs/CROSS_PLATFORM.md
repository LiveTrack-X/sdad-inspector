# Cross-Platform Preview Contract

Status: Active implementation contract
Packets: `SI-005-native-preview`, `SI-006-korean-localization`,
`SI-008-context-workspace-progress-theme`

## Architecture

One Python codebase owns inspection, release-engine authentication, and the
loopback HTTP boundary. React/Vite produces one static frontend. pywebview hosts
that same loopback URL in a native window, and PyInstaller produces an unsigned
one-folder preview. The renderer receives no Python bridge and no direct file or
subprocess capability.

## Platform adapters

| Platform | pywebview engine | Build runner | Current evidence |
| --- | --- | --- | --- |
| Windows | Edge Chromium / WebView2 | `windows-latest` | Local unsigned one-folder build and bounded launch/close smoke passed |
| macOS | Cocoa / WKWebView | `macos-latest` | Workflow configured; runner result not observed |
| Linux | Qt WebEngine under Xvfb in CI | `ubuntu-latest` | Workflow configured; runner result not observed |

pywebview's current platform requirements are documented in its
[installation guide](https://pywebview.flowrl.com/guide/installation) and
[web-engine guide](https://pywebview.flowrl.com/guide/web_engine). PyInstaller
resource paths are resolved relative to bundled module `__file__`, following
its [runtime information guidance](https://pyinstaller.org/en/stable/runtime-information.html).

## Build contract

1. Authenticate the supplied checkout as a supported clean tagged commit or a
   marker-backed archive with the frozen whole-tree digest.
2. Copy the tree to a new staging directory, excluding Git and bytecode only.
3. Write a normalized release marker and reauthenticate the staged tree.
4. Bundle `web/dist` and the staged engine as PyInstaller data directories.
5. Build a one-folder preview on the current OS; never cross-compile a claim.
6. Launch the built artifact against the repository and close it through a
   bounded hidden smoke path.

The matrix uses independent GitHub-hosted runners, as described by GitHub's
[matrix job documentation](https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations).

## Claim and gate limits

- A local Windows pass establishes only that exact Windows environment and
  artifact. It does not establish macOS or Linux execution.
- A configured workflow is not a completed runner result.
- No installer, updater, signing, notarization, artifact upload, publishing, or
  release action is part of this packet.
- Same-release-candidate evidence on all three operating systems plus explicit
  owner authorization is required before a general cross-platform claim.

## Local Windows evidence — 2026-07-15

- Environment: Windows 11 build `10.0.26200`, Python `3.13.11`, pywebview
  `6.2.1`, PyInstaller `6.21.0`.
- Artifact: `build/native/dist/SDAD-Inspector/SDAD-Inspector.exe` in a
  one-folder bundle with 1,311 files and 41,804,247 total bytes. Its complete
  tree SHA-256 is
  `9af64e20fbe1475b1fe96c5cd5b9899e3f932037ce36771ff49a578dcdd2fffd`.
- Executable: 5,603,522 bytes; SHA-256
  `0c2903b39bb2c8c50ea573b91537fe5ea80469fd1f1d2514e342a6ae5bd98e53`;
  Authenticode status `NotSigned`.
- Bundled engine: release `v3.2.2`, peeled commit
  `cd1b1ddb3e6bcb19b531034742c7d67b4257768e`, full-tree SHA-256
  `d475bd6d5428ac7a00de0dc62b4230124ecd5b42a9f8d7789459ee47e4b1c16b`;
  reprobe returned `clean: true` and `trust: release-marker`.
- Runtime: the rebuilt executable launched the current repository through the
  hidden bounded native lifecycle and exited `0` after two seconds before the
  45-second timeout (`timed_out: false`). Browser rendering is separate evidence;
  this smoke proves bounded native launch/close only.
- Shared frontend: the three-file, 364,100-byte bundled `web/dist` tree is
  byte-identical file-for-file to the production source bundle (tree SHA-256
  `e751896800c1482e4634a1a3829a6e639d968e7e41fcb6104c773f16911e945f`).
- Immutability check: the full 1,311-file bundle digest was identical before
  and after the post-build smoke. Both the clean stage and bundled engine
  contained zero `.git`, `__pycache__`, `.pyc`, or `.pyo` artifacts.
- First-smoke negative evidence: the initial build timed out because a frozen
  executable was incorrectly reused as a general Python interpreter. The fixed
  internal runner is restricted to the bundled engine and covered by a
  regression test; `FIND-SI-005-001` records the closure.
- Staging negative evidence: isolated Python initially admitted bytecode cache
  artifacts because `-I` ignores Python environment variables. The final
  source uses `-I -B`, rejects contaminated stages, and records the closure as
  `FIND-SI-005-002`.
