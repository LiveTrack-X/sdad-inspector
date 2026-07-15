# Engine Update And Project Migration Contract

Status: Proposed future packet boundary
Scope: Compatible SDAD engine acquisition and owner-gated project migration

## Version model

Four versions remain separate and visible:

| Contract | Owner | Purpose |
| --- | --- | --- |
| Inspector version | SDAD Inspector | Product UI/core/package identity |
| SDAD engine version | SDAD release | Doctor behavior used for inspection |
| compatibility registry version | SDAD Inspector | Allowed engine, report-schema, and state-schema combinations |
| project state schema | Inspected repository | Repository-local control-file contract |

Inspector must not copy the SDAD engine version into its own product version.
One Inspector release may support multiple authenticated engines, and a new
engine is unsupported until a compatibility packet adds fixtures and evidence.

## Compatible engine update flow

A future opt-in update service may:

1. query only official `LiveTrack-X/spec-driven-ai-development` GitHub Releases;
2. reject branches, dirty worktrees, prereleases unless explicitly selected,
   mutable source archives without the expected release identity, and unknown
   report/state contracts;
3. download into a quarantined versioned cache outside inspected projects;
4. authenticate the complete release tree against a pinned compatibility
   manifest and expected release commit;
5. run the frozen Doctor fixture/self-test contract before activation;
6. atomically select the compatible engine while retaining the previous engine
   for rollback.

Automatic checking and selection among already authenticated cached engines can
be enabled. Network download must be opt-in and observable. A failed download,
authentication, or self-test leaves the active engine unchanged. The current
preview remains offline and uses only its bundled authenticated v3.2.2 engine.

## Project bootstrap and migration flow

Engine acquisition never authorizes a project write. Project application is a
separate operation with this fixed sequence:

1. read-only discovery of current state, schemas, and repository controls;
2. a version-targeted migration/bootstrap recommendation;
3. a complete preview listing every create, update, move, and delete action;
4. explicit owner approval for that exact preview and project root;
5. a recoverable snapshot or backup plus a transactional apply boundary;
6. post-apply Doctor and contract validation;
7. automatic rollback on failed verification, followed by an evidence report.

Preview may run as a Standard read-only packet. Apply requires Full SDAD and the
`auto-fix/write` owner gate. Release, signing, publishing, and updater
distribution retain their independent owner gates. Approval for one preview is
not reusable after its inputs, engine, project tree, or generated diff changes.

## Proposed packet split

- `engine-registry`: read-only compatibility registry and authenticated local
  cache selection;
- `engine-download`: opt-in GitHub Release discovery, quarantine, verification,
  rollback, and network/error UX;
- `migration-preview`: project-specific, read-only migration plan and complete
  diff generation;
- `migration-apply`: Full-scale owner-gated backup, transactional write,
  verification, and rollback;
- `product-updater`: separately signed Inspector package update and rollback.

## Evidence required before claims

- Official release identity, immutable manifest/checksum, compatibility fixture
  results, cache rollback, and corrupted-download rejection.
- Preview determinism and proof that preview performs zero project writes.
- Apply/rollback fault-injection evidence across supported filesystems and all
  claimed operating systems.
- Same-release-candidate install/update/rollback evidence plus signing or
  notarization before distributing an Inspector product updater.

Until those packets pass, the product may describe the architecture only. It
must not claim automatic SDAD updates or safe automatic project migration.
