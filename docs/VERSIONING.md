# Product and protocol versioning

Status: Active policy from release 3.2.4 onward

Inspector and its default bundled SDAD Protocol use the same release number
starting with Inspector 3.2.4. This identifies a release family, not a shared
repository, artifact, schema or verification result.

| Item | Current fact |
| --- | --- |
| Inspector product version | 3.2.4 |
| Default bundled engine | Released SDAD Protocol 3.2.4, authenticated by immutable identity |
| Published Inspector | [3.2.4](https://github.com/LiveTrack-X/sdad-inspector/releases/tag/v3.2.4); bundles SDAD Protocol 3.2.4 |
| Previous Inspector release | 0.0.5; retains its original bundled SDAD Protocol 3.2.3 |
| Historical releases | Original tags, assets, checksums, notes and results stay unchanged |
| Explicit source-mode engine selection | Supported authenticated 3.2.1, 3.2.2, 3.2.3 or 3.2.4 |
| State / Doctor report / Inspector snapshot schemas | State 1–2, report 1–2, snapshot 2; no migration introduced |

The jump from Inspector 0.0.5 to 3.2.4 aligns numbering with the existing Protocol
release. It does not claim years of product maturity, signed distribution,
broader platform support, user acceptance or a new state schema. Protocol 3.2.4
was already released; this alignment did not retag or republish that repository.

## Authorities and generated text

`sdad_inspector/version.py` owns the Inspector product version. Protocol owns its
own version and immutable released commit. Inspector separately records each
supported engine's commit and authenticated tree digest in `sdad_inspector/engine.py`;
the [integration contract](SDAD_INTEGRATION_CONTRACT.md) documents this boundary.
Runtime observations must continue to show the engine actually selected, even
when its version differs from the Inspector product.

`python scripts/release_metadata.py --sync` updates Windows version resources and
the single managed source-version block in each README. It does not infer that
a release exists, rewrite download URLs or rewrite historical notes. `--check`
requires exactly one complete current block per README and matching resources.
Candidate notes must explicitly say they are unpublished until publication is
verified. Published download guides change only after the corresponding release
and asset identity are confirmed.

## Paired release procedure

1. Select one unused shared version for the intended pair. Scope and version
   changes are authorized work; commit, push, tag and publication remain separate
   actions requiring the applicable owner authorization.
2. Validate Protocol under its own rules and establish its immutable released
   commit and authenticated content. Preserve its raw results and failures.
3. Pin that exact Protocol identity in Inspector, retain supported older engine
   identities, and capture/replay the required compatibility fixtures. A matching
   string alone never authenticates an engine.
4. Build Inspector with a clean authenticated engine whose version equals its
   product version. Native preparation rejects mismatches, even when the older
   engine is supported for explicitly selected source inspection.
5. Complete Inspector's own same-commit main checks, native builds, direct and
   downloaded smokes. With release authorization, promote those exact archives
   through the tag gates described in [release maintenance](RELEASING.md).
6. Report each repository's tag, commit, workflow outcomes, artifacts and actual
   publication state separately. A pair is published only when both publications
   are confirmed. Update current download guides from those observed results.

A shared number is not a cross-repository transaction. If Protocol is published
and Inspector fails, report that partial state and retain failure evidence. Do
not move the Protocol tag, replace assets, or claim Inspector was published.
Retry only within the documented immutable-candidate recovery rules. Changed
release content that requires a new tag uses a new unused shared version;
otherwise defer the unfinished partner without inventing a completed pair.

## Update and compatibility limits

The product updater compares product versions; published 3.2.4 is newer than
0.0.5. It must still verify the exact platform asset and digest
before replacement. A candidate version or passing unit test is not proof of an
end-to-end published update. The new executable carries its declared embedded
engine; no separate automatic engine acquisition or project migration is added.

Continue to distinguish product version, actual engine version, state schema,
Doctor report schema, Inspector snapshot schema, command result and user
acceptance. Matching version numbers do not authorize project writes, automatic
state promotion, release, signing or acceptance claims.
