# Optional verification receipts

This is an opt-in local observation format. It does not change State v2,
Doctor JSON, packet status, acceptance, or release authority. Inspector never
executes a command from a receipt or validation declaration.

## Record an explicitly selected command

The protocol source provides `scripts/sdad_evidence.py`. It is a separate CLI,
not part of the bundled released engine. Use its actual checkout path. From a
project with an existing `docs/evidence` directory, for example:

```text
python /path/to/protocol/scripts/sdad_evidence.py --project . --output docs/evidence/P1-check-01.json --file src/example.py --file tests/test_example.py --packet P1 --requirement R1 --scope "example behavior" --timeout 120 --log-bytes 4096 -- python -m unittest tests.test_example
```

All file paths are normalized, project-relative, forward-slash paths. `--cwd`
defaults to the project root; source paths remain relative to that root even
when cwd differs. Use the project's existing evidence directory; no required
directory or new startup document is introduced. The output parent must exist.
The new `.json` receipt and `.json.log` sibling must not exist or overlap a
declared source. Existing files are never overwritten. No state, TODO, or other
control file is updated by the recorder. The selected command itself can write
files: this tool is not a sandbox and does not authorize protected actions.

The command is launched with `shell=False`, no input, and merged stdout/stderr.
Arguments are stored verbatim; do not put secrets in arguments. Log text is
**not retained by default** (`--log-bytes 0`). Opt-in retention stores only a
prefix, up to 64 KiB, while counting all drained bytes. The digest covers the
retained bytes, not omitted output. No environment-variable dump is captured.
Review a receipt before sharing; hashes are not redaction or authentication.

Windows uses a Job Object assigned while the process is suspended, before it
can spawn children. The job terminates descendants on timeout, interruption,
or root-process exit. POSIX uses a new process group and terminates that group;
a command that deliberately detaches can escape it. Run trusted bounded checks,
not services or hostile commands. Abrupt recorder termination can leave an
incomplete placeholder, never a fabricated success receipt. A failed capture
uses a fresh output name on retry; preserve the previous attempt.

## Preview registration after collecting

Use the source checkout's separate read-only preview mode for one explicit
receipt, then review its suggested change to existing `routed_docs`:

```text
python /path/to/protocol/scripts/sdad_evidence.py --project . --preview-connection docs/evidence/P1-check-01.json
```

Only `--project` and `--preview-connection` are accepted in this mode. It validates
the receipt v1 envelope (64 KiB maximum) and root State v2 file (64 KiB and 500
lines maximum). It refuses proposals whose resulting state would exceed either
limit. Inspector's `.env*` exclusion applies to receipt, command directory,
source and log metadata paths.
It prints `registration: already_registered` with no suggestion, or
`registration: missing` with a minimal `suggestion` containing one-based
`start_line`, `delete_count`, `expected_lines`, `replacement_lines` and a readable
instruction. Review those lines; other routes, comments and line endings are
preserved. Paths are safely quoted in the proposed YAML.

The output includes `state_sha256`, `receipt_sha256`, `current_packet` and
`receipt_packet`. Rerun preview after the state or receipt changes; the line edit
belongs to the observed state digest. The tool never applies it. Invalid,
missing, unsafe or unsupported receipt/state inputs produce exit code 2, an
error on stderr, and no proposal on stdout. A valid failed or historical receipt
can be selected without being relabeled as current success. Existing registered
receipts are still validated before reporting that no edit is needed.

Preview does not discover files, change state/TODO, execute a command, compare
current source/log bytes, or establish acceptance. Registering a path only makes
the record eligible for Inspector's explicit reads. Keep the original receipt
as the run record; the suggestion is a connection aid, not another evidence file.

## Version 1 contract

The JSON object has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema`, `version` | `sdad.verification-receipt`, integer `1` |
| `id`, `packet`, `requirement`, `scope` | Record identity and explicitly supplied scope; not proof that scope was exercised |
| `cwd` | `.` or a project-relative command directory |
| `command` | `argv` array, recorder `python_version`, and `platform`; no inferred executable/tool version |
| `started_at`, `ended_at` | UTC observation timestamps; not authority or uniqueness |
| `outcome`, `exit_code` | `passed`/0, `failed`/nonzero, or `timeout`, `start_failed`, `interrupted`/null |
| `source_stability` | `stable`, `changed`, or `unknown` from before/after observations |
| `sources` | 1–32 `{path, before, after, error}` observations; each identity is `{sha256, size}` or null |
| `log` | `{path, sha256, bytes, total_bytes, truncated, complete}`; path relative to project |
| `limits` | Human-readable limits, including no semantic verification or acceptance |

Relevant files are bounded at 2 MiB each. Missing, oversized or unreadable
sources stay unknown. Changed-before/after bytes remain changed even if the
current file later matches the after hash. Only boundary snapshots are observed:
temporary modifications that are reverted during a command can be missed.
Undeclared dependencies, external services and environment changes are not
covered. Exit zero says only that the selected process returned zero.

## Inspector read-only projection

Explicitly add a chosen receipt `.json` path to the existing state's
`routed_docs` only when it should be available. The recorder does not add it.
Inspector does not recursively discover receipts or follow links from arbitrary
Markdown. A routed JSON file that is not a valid receipt is a visible diagnostic.

The primary navigation flow lists registered JSON paths before reading a chosen
record. `POST /api/verification-receipt-list` accepts `project_root`, optional
integer `offset` (default 0), and `revision`. It returns `version: 1`,
`project_root`, current `packet`, `read_at`, `revision`, `offset`, `total`,
`next_offset` (integer or null), and `paths`. Each page contains at most 10 paths.
Listing reads bounded state bytes only; it does not open receipts, sources or
logs. Later pages require the revision from the first page.

`POST /api/verification-receipt-inspect` accepts `project_root`, one registered
`path`, and the list `revision`. It returns `version: 1`, `project_root`, current
`packet`, `read_at`, `revision`, and one `observation` in the item format below.
The revision binds the selected project, state bytes, current packet and eligible
registered paths. Refresh the list after a state change. Each explicit selection
has its own source-comparison budget, so earlier records do not consume it.
Missing or malformed selected receipts remain visible diagnostics. Registration
is required; arbitrary JSON paths are not an alternative read route.

For compatibility, the older bulk `POST /api/verification-receipts` and
`load_verification_receipts(root, *, state=None)` return `project_root`, current
`packet`, `read_at`, `receipts`, and `truncated`. Each item has `path`, `receipt`
(the validated object or null), `source_match`, `log_match`, `sources`, and
`error`. Each source comparison has `path`, `match`, and `reason`.

- `matched`: the named bytes match at this observation. It is not semantic
  verification, trust in the receipt's author, or current external availability.
- `changed`: the declared source changed during or since the run, or retained log
  bytes differ from their digest. Source and log comparisons are separate.
- `unknown`: evidence is missing, unsafe, malformed, unsupported, or exceeds the
  inspection budget. Unknown is never reported as no problems or a passing check.

Selected inspection reads one receipt, at most 64 KiB, with 2 MiB per source and
16 MiB total source contents, plus 64 KiB per retained log. The legacy bulk read
still reads only the first 10 registered JSON paths and shares the 16 MiB source
budget; its `truncated` flag signals omitted entries. Use paged selection to reach
later records without reordering state. Paths
must stay within the selected project; sensitive classes, symbolic links and
hard links are rejected. Duplicate JSON fields, unknown schema versions, extra
fields and contradictory outcome/stability metadata are rejected. Reading does
not write, execute, upgrade state, or accept work. Historical packet receipts
remain historical even when their file hashes match.

Raw execution outcome, source comparison, log integrity and capture limits must
stay distinct in UI and exports. A retained-log match may coexist with truncated
or incomplete output. Recheck explicitly after edits; results are observations
at `read_at`, not a background guarantee.

## Shared conformance checks

`tests/fixtures/verification-receipts` is an identical, digest-pinned copy of
Protocol's authoritative synthetic corpus. Both projects independently pin the
manifest; the case data and portable fixture helper are checked before use.
The corpus covers current/historical/unknown observations, outcomes, incomplete
capture, invalid envelopes, actual synthetic `.env*` metadata paths, and receipt
and state read limits including a proposed registration that would overflow.

Run the offline reader gate without a Protocol checkout:

```text
python scripts/validate_receipt_compatibility.py
```

For checkout integration, explicitly select a trusted local Protocol source:

```text
python scripts/validate_receipt_compatibility.py --protocol-checkout /explicit/trusted/protocol-checkout
```

The latter also verifies identical corpus bytes, invokes the real preview CLI,
applies its hash/line-bound suggestion only inside a temporary synthetic project,
and verifies listing, selected inspection, the unchanged legacy response, and
preview idempotence. Preview and reader operations must preserve file fingerprints.
There is no network fetch, installed-engine import or application runtime coupling.
These are compatibility cases; they do not establish productivity, user acceptance
or platform support without actual platform test runs. Corpus changes originate
in Protocol and require reviewed manifests and pins; see its copied README.
