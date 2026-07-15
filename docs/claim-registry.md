# Claim Registry

Status: Active
Scope: Wording allowed by current SDAD Inspector evidence

## Registry

| ID | Claim text or pattern | Status | Severity | Allowed locations | Evidence | Required qualifier | Blocked locations | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLAIM-SI-001 | Packet 0 contains normalized Doctor fixtures from released SDAD v3.2.1 and v3.2.2 tags | allowed_with_qualifier | P2_qualified | SPEC, Packet 0 report, developer docs | EVID-SI-001, EVID-SI-002 | `fixture-contract evidence only` | Release title, product marketing | Does not imply Inspector implementation |
| CLAIM-SI-002 | SDAD Inspector supports Windows, macOS, and Linux | blocked_until_evidence | P1_evidence_required | None | EVID-SI-004 | None | README headline, UI, release notes, package metadata | Same-RC evidence required on all three OSes |
| CLAIM-SI-003 | SDAD Inspector is release-ready or production-ready | blocked_until_evidence | P1_evidence_required | None | Future release evidence and owner decision | None | All public surfaces | Packet 0 is not release evidence |
| CLAIM-SI-004 | SDAD Inspector can safely auto-fix or write a project | forbidden | P0_forbidden | None | None | None | All current product surfaces | Out of scope and owner-gated |
| CLAIM-SI-005 | The read-only core, browser UI, and static report are locally verified on Windows | allowed_with_qualifier | P2_qualified | README, developer docs, local UI | EVID-SI-003, EVID-SI-005, EVID-SI-006 | `local Windows evidence; no release or other-OS implication` | Release title, cross-platform marketing | Validation commands remain metadata only |
| CLAIM-SI-006 | An unsigned Windows one-folder preview built and completed a bounded local launch smoke | allowed_with_qualifier | P2_qualified | README, developer docs, local handoff | EVID-SI-007 | `unsigned local preview; exact recorded artifact only` | Release title, installer claim, production marketing | Does not establish install, upgrade, signing, or distribution |
| CLAIM-SI-007 | Exact same-commit Windows X64, macOS ARM64, and Linux X64 hosted preview artifacts built and passed full contracts plus direct and separate downloaded-archive smoke | allowed_with_qualifier | P2_qualified | Developer docs, candidate report | EVID-SI-004, EVID-SI-014 | `exact unsigned alpha.3 candidate commit 7eaec5c on current GitHub-hosted runner images; tag and published assets pending` | Product support headline, stable-release claim | Hosted-runner candidate evidence is not a general operating-system support commitment |
| CLAIM-SI-008 | SDAD Inspector provides Korean and English product UI | allowed_with_qualifier | P2_qualified | README, developer docs, local UI | EVID-SI-008 | `product-owned chrome only; repository evidence remains verbatim; local Windows evidence` | General machine-translation claim, additional-language claim, cross-platform support headline | Browser-locale detection and explicit local selection share one browser/native frontend bundle |
| CLAIM-SI-009 | A folder without readable SDAD state shows Doctor diagnostics instead of a blank screen | allowed_with_qualifier | P2_qualified | README, developer docs, local UI | EVID-SI-009 | `verified locally on Windows for the normalized missing-state contract` | General cross-platform or malformed-contract resilience claim | Browser and exact rebuilt unsigned preview were exercised against the reported folder |
| CLAIM-SI-010 | SDAD Inspector provides tree-driven central evidence views, observed inspection progress, and persisted light/dark themes | allowed_with_qualifier | P2_qualified | README, developer docs, local UI | EVID-SI-010 | `local Windows evidence; progress describes Inspector observation only; exact shared bundle` | Repository work-phase claim, cross-platform support headline, automatic update/apply claim | Progress contains no synthetic percentage and does not infer Plan/Route/Implement/Verify/Report for the inspected repository |
| CLAIM-SI-011 | SDAD Inspector automatically updates SDAD or safely migrates projects | blocked_until_evidence | P1_evidence_required | Future design documentation and an explicitly labeled future README section only | Future update/migration evidence | `proposed architecture only` | Current UI feature list, release title, product marketing | Engine acquisition and project writes are separate; apply remains Full and owner-gated |
| CLAIM-SI-012 | SDAD Inspector shows the active packet, its TODO checklist, live Markdown, observed Git worktree/commit metadata, handoff history, and manual or 15-second AUTO refresh | allowed_with_qualifier | P2_qualified | README, developer docs, local UI | EVID-SI-011 | `local Windows evidence; observed paths are not causal attribution; no guessed work times` | Cross-platform support headline, author-identity claim, automatic update/apply claim | The shared browser/native frontend uses authenticated bounded reads; owner gates remain stopped |
| CLAIM-SI-013 | SDAD Inspector uses one active-packet TODO source, one coherent refresh cadence, localized Git labels, an evidence-limited five-stage flow, stable recent projects, and a view-before-save Rule 5 proposal export | allowed_with_qualifier | P2_qualified | Developer docs, local UI | EVID-SI-012 | `local Windows evidence; Rule 5 output is an inactive proposal saved outside the inspected repository` | Active-rule claim, automatic enforcement/adoption claim, cross-platform support headline, release title | Save requires a complete current finding, exact preview digest, explicit confirmation, and a cancellable system Save As choice; owner gates remain stopped |
| CLAIM-SI-014 | SDAD Inspector provides safe Markdown heading navigation, responsive routed-document disclosure, stage-filtered changed paths, accessible narrow scan controls, and Git status aligned with the owner's effective system line-ending policy | allowed_with_qualifier | P2_qualified | Developer docs, local UI | EVID-SI-013 | `local Windows evidence; filtering does not alter classification; exact isolated unsigned preview only` | Cross-platform support headline, causal work-stage claim, signed/released artifact claim | Owner acceptance and macOS/Linux execution remain unobserved; owner gates remain stopped |
| CLAIM-SI-015 | The 0.0.1 alpha release is a portable single-file application that needs no separately installed Python runtime | blocked_until_evidence | P1_evidence_required | None | EVID-SI-014 | `exact unsigned tagged artifacts and tested hosted-runner environments only` | README headline, release title, broad OS support claim | Requires CPython 3.12 one-file builds plus post-download clean-runner smoke on Windows, macOS, and Linux |

## Stop Rules

- Do not upgrade a claim from Doctor green or local fixture tests.
- Release, signing, publishing, and auto-fix/write require explicit owner authorization.
- If forbidden or unsupported wording appears, stop the affected publication or distribution.

## Owner Decision References

The owner selected Split Inspector concept 3 and asked implementation to
continue through completion. No owner acceptance of the resulting evidence is
recorded.

- `OWNER-SI-012-PUBLIC-SOURCE-001` — On 2026-07-15 the owner explicitly directed
  publication of this checkout as a public GitHub repository. This authorizes
  repository creation and source push to
  `https://github.com/LiveTrack-X/sdad-inspector` only. It does not authorize a
  GitHub Release, artifact or package upload, signing, notarization, deployment,
  automatic project write, license grant, or broader product/support claim.

- `OWNER-SI-013-ALPHA-RELEASE-001` — On 2026-07-15 the owner explicitly
  directed README and repository cleanup plus a `0.0.1 alpha` release built by
  CI for macOS, Windows, and Linux. With no signing credentials configured, this
  authorizes one clearly labeled unsigned GitHub prerelease containing exactly
  three same-commit platform archives and SHA-256 checksums. It does not
  authorize a stable release, installer, updater, signing, notarization,
  package-registry publication, deployment, automatic project write, or broad
  operating-system support claim.

- `OWNER-SI-013-PORTABLE-002` — On 2026-07-15 the owner clarified that the
  authorized alpha release must use single-file portable executables built and
  released by CI so copying only the executable does not depend on an adjacent
  Python runtime directory. This supersedes only SI-013's prior one-folder
  packaging layout; all unsigned-alpha limitations and protected-action
  exclusions remain unchanged.
