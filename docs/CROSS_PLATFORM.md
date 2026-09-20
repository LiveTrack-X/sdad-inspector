# Cross-Platform Portable Contract

Status: Active public implementation contract

## Architecture

One Python codebase owns inspection, bundled-engine authentication, the closed
loopback service, the native shell, and product-update verification. React/Vite
produces one static frontend. pywebview opens that same authenticated loopback
URL in a native window. PyInstaller produces an unsigned one-file executable
with CPython 3.12, the web bundle, and the authenticated SDAD 3.2.3 engine
embedded.

Inspector orchestration reaches that engine through the built-in
`official-sdad-3` protocol adapter and emits Inspector snapshot schema 2. The
adapter registry is separate from the renderer and from product update logic;
the 0.0.5 portable packages do not discover or download additional adapters.

The renderer receives no general Python bridge, filesystem bridge, or subprocess
capability. The packaged product updater is exposed only through fixed
authenticated loopback routes; source/browser mode reports it as unsupported.

## Published release targets

| Platform | UI engine | GitHub runner | Release asset |
| --- | --- | --- | --- |
| Windows x64 | Edge Chromium / WebView2 | `windows-latest` | `SDAD-Inspector-0.0.5-windows-x64.zip` |
| macOS arm64 | Cocoa / WKWebView | `macos-latest` | `SDAD-Inspector-0.0.5-macos-arm64.tar.gz` |
| Linux x64 | Qt WebEngine; Xvfb in CI | `ubuntu-latest` | `SDAD-Inspector-0.0.5-linux-x64.tar.gz` |

The table names exact build targets, not every machine supported by the
operating-system family. pywebview's platform dependencies are documented in
its [installation guide](https://pywebview.flowrl.com/guide/installation) and
[web-engine guide](https://pywebview.flowrl.com/guide/web_engine).

## Build and portable-smoke contract

1. Authenticate the supplied SDAD checkout as supported clean release content.
2. Copy it to a new stage, excluding Git and bytecode artifacts, then
   reauthenticate the complete stage.
3. Build the frontend and bundle it, the staged engine, pywebview, and the
   generated platform icon with official CPython 3.12.
4. Produce one executable on the current OS; never cross-compile an execution
   claim.
5. Launch that executable against a disposable fixture with isolated app
   preferences. Check receipt pagination through the eleventh record, malformed
   receipt rejection, selected source/log identity and unchanged project bytes
   through the actual authenticated loopback API, then close the native window
   through the hidden smoke lifecycle. Synthetic receipts are not verification
   evidence for a real project. This is not native visual interaction coverage.
6. Archive only that regular executable, preserving the POSIX executable bit.
7. Give the archive to a separate clean hosted runner which checks member count,
   member type and name, extracts it without product dependency installation,
   and repeats the launch smoke.
8. After all main-push build and downloaded-smoke jobs succeed, bind the three
   archives to their exact commit, version, run/attempt and hashes in the candidate
   manifest. A future authorized tag promotes that same candidate without
   rebuilding, after identity checks and another three-platform downloaded smoke.
9. Write `SHA256SUMS`, attest all five assets (three archives, checksums and the
   candidate manifest), upload to a new draft, and publish only after every
   required job succeeds. Never replace an existing public tag or Release.

Each release needs its own successful hosted runs; this contract alone does not
establish a result. Published 0.0.4 artifacts and historical evidence remain unchanged.
[Release maintenance](RELEASING.md) documents the single version authority,
three-day candidate retention, rejection rules and retry procedure.

PyInstaller resource lookup follows its
[runtime information guidance](https://pyinstaller.org/en/stable/runtime-information.html).

## Product self-update contract

The same platform and architecture naming contract selects a future update.
The packaged app accepts only a strictly newer immutable release from the
canonical GitHub repository and requires GitHub's SHA-256 asset digest, bounded
size and redirects, and one exact regular executable archive member.

The verified executable is staged in per-user app data. A copied new executable
acts as the replacement helper. It waits for the running PyInstaller parent,
retains one previous executable, atomically replaces the original path, and
relaunches the selected project. Windows waits for the one-file bootloader
parent so the target lock is released before replacement. Failed replacement
restores and relaunches the previous version when possible and blocks automatic
retry loops.

On Windows, a verified replacement and every normal frozen-app startup notify
the shell about the exact executable path before refreshing icon associations.
This is a cosmetic same-path cache repair; failure never blocks startup,
replacement success, or rollback.

The product updater never changes the inspected repository or the bundled SDAD
engine. It is an unsigned-portable update path, not an installer, signing,
notarization, upgrade/uninstall, or stable-support guarantee.

## Platform prerequisites

- Windows needs WebView2. The portable EXE includes Python and application
  packages but not this operating-system web component.
- macOS currently publishes an Apple Silicon arm64 executable. It is unsigned
  and not notarized.
- Linux needs a graphical desktop and the EGL/GL/XCB/Qt WebEngine runtime stack
  installed by the workflow. A `noexec` temporary filesystem is outside the
  one-file launch evidence.

## Claim limits

- A local result establishes only that exact environment and artifact.
- A configured workflow is not a completed hosted-runner result.
- A passing Windows/macOS/Linux matrix establishes the exact tagged artifacts
  and recorded runner images, not every OS version, security product, display
  server, GPU, filesystem, or physical computer.
- This release remains unsigned. General support, installer,
  signing/notarization, deployment, package-registry, and stable claims require
  independent evidence and authorization.
