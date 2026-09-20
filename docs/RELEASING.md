# Maintaining a release candidate

Current published release: [Inspector **3.2.4**](https://github.com/LiveTrack-X/sdad-inspector/releases/tag/v3.2.4),
with default bundled SDAD **3.2.4**. Historical Inspector **0.0.5** bundles SDAD
**3.2.3**; its tag, archives and release notes remain unchanged. Read the
[versioning policy](VERSIONING.md) before preparing a paired release.

`sdad_inspector/version.py` is the current Inspector version authority. Setuptools,
the runtime, release checks and CI outputs derive their values from it. To prepare
an authorized future version change, edit that file, run
`python scripts/release_metadata.py --sync`, and add its release notes under
`docs/releases/v<version>.md`. Sync regenerates Windows numeric/string resources
and only the managed source-version block in each README. It does not rewrite
published download links, publication claims or historical release notes.
Run `--check` to detect stale resources and missing, duplicate, malformed or stale
README blocks. Matching release numbers do not merge product and engine identities:
the selected engine, authenticated tree and schemas remain separate compatibility facts.

Before a native candidate build, authenticate the exact released SDAD checkout
and require its version to equal the Inspector product version. A supported older
engine remains usable for explicit source inspection; that does not authorize
bundling it under a different shared release number. For the initial 3.2.4
alignment, use the already released Protocol 3.2.4 identity; do not recreate or
republish its tag. Future paired releases need both repositories' own gates and
publication evidence. A published Protocol and failed Inspector candidate must
be reported separately, never as a successfully published pair.

## Candidate identity and promotion

1. With the owner's separate push authorization, push the intended release commit
   to `main`. Cross-platform checks retain the full Python/frontend/audit,
   native build, branding, direct smoke and downloaded portable smoke gates.
   `--verify-receipts` exercises the packaged receipt APIs with disposable fixture
   data and isolated app preferences outside that fixture, while checking that
   inspection preserves every project file. No user settings are replaced.
2. Only a successful main push can produce `verified-release-candidate`. Its
   `candidate-manifest.json` binds the source commit, Inspector version, repository,
   workflow run/attempt, and exact names, sizes and SHA-256 hashes of all three
   platform archives. Retention is three days. Local scripts cannot establish
   hosted success merely by creating a manifest.
3. After success and explicit owner release authorization, create the version
   tag at that exact commit. Never move or replace an existing public tag,
   including a tag from a failed release attempt. A changed release source needs
   a new unused version; retain failure evidence.
4. The tag workflow selects a successful same-commit main candidate using GitHub
   run metadata. It rejects fork/PR, failed/incomplete, wrong-branch, wrong-workflow,
   commit/version/run mismatches and altered archive bytes. It downloads the
   verified bundle and repeats the independent three-platform portable smokes.
   It does not rebuild the executables under the tag.
5. Publication rechecks the manifest and remote tag, creates checksums, attests
   the archives/checksums/candidate manifest, uploads without replacement, then
   publishes the draft. Existing Releases are refused; no automatic approval,
   tag movement, release overwrite, or signing claim is introduced.

The promoted release has five assets: three platform archives, `SHA256SUMS`, and
the additional `candidate-manifest.json` provenance record. The updater selects
its exact platform archive by name and ignores the other assets. The manifest
does not change archive members or replace GitHub's asset digest validation.
Ordinary CI push triggers cover branches only; tag pushes run promotion without
starting a second set of native builds. PR and manual CI remain available.

Expired/missing artifacts stop promotion. Rerun the original same-commit main
push checks and confirm a fresh successful candidate before retrying the tag
workflow; do not substitute a different commit's binaries or change a published
tag. A newer run attempt must have its own matching manifest. Re-running does
not renew or expand the owner's authorization.

If a failure happens after draft creation, a full rerun deliberately refuses the
existing draft. Inspect the unpublished draft, completed attestations and uploaded
asset hashes against the exact same candidate before an explicitly authorized
recovery. Do not delete or overwrite a published release, replace assets, move a
tag, or assume that an existing draft completed any later gate.

Local manifest tests establish rejection and identity behavior, not hosted
Actions success or production safety. Check the exact main and tag workflow
results for each authorized release. Manifest hashes bind
content within the trusted repository's Actions boundary; they do not replace
the final artifact attestations, signing, or independent source review.
