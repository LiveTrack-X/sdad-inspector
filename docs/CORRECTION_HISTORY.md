# Keeping and recovering correction drafts

Open **Manage correction history** in the request/interpretation panel. Active
storage is shared across projects and limited to 40 records and 512 KiB. The
usage label includes other projects; the record list contains only the selected
project. Switch projects to manage their records.

**Archive** asks for confirmation and frees active capacity without deleting the
record. The archived view shows 20 records per page. **View** retains the original
identity and exact response matching; it never treats archiving as delivery,
application, verification or acceptance. **Restore** returns the same record to
active storage and checks available capacity. A copied/prepared correction stays
immutable. If another window changed the record, refresh history before retrying.

**Copy recovery JSON** exports one complete record, including its project,
packet, request, revision and supersedes identity. Preserve that text outside
the app if needed. Paste it into **Recovery JSON** and explicitly restore it
while the original project is selected. Import cannot replace different content
under an existing ID or move a correction to another project. There is no
automatic deletion or export to an inspected repository.

## Storage and older Inspector versions

Normal saves continue using the existing app-data JSON. The first explicit
Archive action retains its exact `.legacy.json` backup and activates a local
SQLite history store next to it. The JSON entrypoint becomes a versioned marker;
older Inspector versions reject it rather than overwrite newer records. This
changes app-owned storage only, not project files or the SDAD state schema.

To back up the complete history, close Inspector and preserve its app-data
directory, including the marker, `.sqlite3` database and legacy backup. The
legacy backup represents the moment before archiving; it does not contain later
saves. Do not replace the current marker with that older backup as a normal
rollback. Keep the complete directory and use a compatible Inspector to export
or restore records. Storage errors preserve existing data and do not trigger
automatic resets.

## Item corrections after source changes

Item correction text remains in the current page session while navigating or
refreshing project evidence. A changed source version offers the previous draft
with old/current text and source identity. If a TODO moved to a different line,
open **Other saved drafts in this document** to compare manually. This list is
limited to the same project, packet and document; no correspondence is inferred.
Carry-forward requires an explicit action and never overwrites a nonempty input.
These item drafts still do not survive a full page reload and have no automatic
agent delivery or response tracking.
