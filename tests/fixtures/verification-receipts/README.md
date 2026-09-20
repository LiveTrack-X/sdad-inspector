# Shared receipt conformance corpus v1

Protocol owns `cases.json` and the portable synthetic `fixture_helper.py`.
`manifest.json` pins their exact SHA-256 bytes. Protocol's conformance test and
Inspector's checkout checker separately pin the manifest itself. Inspector keeps
an identical copy under `tests/fixtures/verification-receipts`; no runtime fetch
or dependency is introduced. JSON and Python files use LF on every platform.

Cases cover current/historical packets; all five outcomes; missing/changed source
observations; truncated/incomplete capture; invalid and duplicate-field envelopes;
actual synthetic `.env*` receipt/cwd/source/log paths; and receipt/state 64 KiB and
500-line boundaries, including registration proposals that would overflow.
File contents and path names are synthetic. They contain no credentials.

Run Protocol's normal unittest discovery, or:

```text
python -m unittest discover -s tests -p test_receipt_conformance.py -v
```

From an Inspector checkout, validate the pinned reader copy without Protocol:

```text
python scripts/validate_receipt_compatibility.py
```

Exercise the actual Protocol preview CLI, its hash/line-bound suggested state
edit, Inspector's list/selected/legacy reads, and preview idempotence:

```text
python scripts/validate_receipt_compatibility.py --protocol-checkout /explicit/trusted/protocol-checkout
```

The integration checker applies suggestions only inside temporary synthetic
projects. Preview and Inspector reads must preserve complete file fingerprints;
only fixture setup and explicit test application may write those fixtures.
Receipt commands are never run by preview or the reader. Platform-neutral Python
tests still require real Windows/macOS/Linux CI execution before a platform claim.

When intentionally changing the contract, update cases/helper in Protocol,
regenerate the manifest's two hashes, review and update both consumer manifest
pins, copy all corpus files byte-for-byte, then run the cross-checkout command.
Do not refresh digests merely to make an unexplained mismatch pass. These cases
check compatibility and boundaries, not semantic verification or productivity.
