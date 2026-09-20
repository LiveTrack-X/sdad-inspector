import {useEffect, useState} from 'react';
import {getCorrectionHistory, importCorrection, manageCorrection, type CorrectionHistory as History, type CorrectionUsage} from '../api';
import {correctionError} from '../correctionErrors';
import type {InteractionCopy} from '../interactionCopy';
import type {Correction} from '../interactions';

type Props = {root: string; copy: InteractionCopy; usage?: CorrectionUsage; onChange: () => void; onView: (row: Correction, archived: boolean) => void};
export function CorrectionHistory({root, copy: c, usage, onChange, onView}: Props) {
  const [open, setOpen] = useState(false);
  const [archived, setArchived] = useState(false);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<History | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState<Correction | null>(null);
  const [recovery, setRecovery] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!open) return;
    let current = true;
    setBusy(true); setPage(null); setPending(null);
    getCorrectionHistory(root, archived, offset).then(value => {if (current && value.project_root === root && Array.isArray(value.drafts)) setPage(value);})
      .catch(error => {if (current) setMessage(correctionError(error, c));}).finally(() => {if (current) setBusy(false);});
    return () => {current = false;};
  }, [root, open, archived, offset, refresh]);
  const measured = page?.usage ?? usage;
  async function changeHistory() {
    if (!pending) return;
    setBusy(true); setMessage('');
    try {
      await manageCorrection(root, archived ? 'restore' : 'archive', pending);
      setPending(null); setMessage(archived ? c.restoredSaved : c.archivedSaved); setRefresh(n => n + 1); onChange();
    } catch (error) {setMessage(correctionError(error, c));} finally {setBusy(false);}
  }
  async function exportRow(row: Correction) {
    setMessage('');
    try {await navigator.clipboard.writeText(JSON.stringify({schema_version: 1, kind: 'sdad-correction-export', draft: row}, null, 2)); setMessage(c.exported);}
    catch {setMessage(c.clipboardError);}
  }
  async function restoreExport() {
    setBusy(true); setMessage('');
    try {
      if (new TextEncoder().encode(recovery).length > 512 * 1024) {setMessage(c.invalidError); return;}
      let parsed: unknown;
      try {parsed = JSON.parse(recovery);} catch {setMessage(c.invalidError); return;}
      await importCorrection(root, parsed); setRecovery(''); setMessage(c.imported); setRefresh(n => n + 1); onChange();
    } catch (error) {setMessage(correctionError(error, c));} finally {setBusy(false);}
  }
  return <details className="correction-history" open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{c.manageHistory}</summary>
    {open && <>
    {measured && <p>{c.usage}: {measured.active_count}/{measured.active_limit} · {measured.active_bytes}/{measured.byte_limit} {c.bytes} · {c.archivedCount}: {measured.project_archived_count}</p>}
    <p>{c.historyScope}</p>
    <div className="correction-actions">
      <button type="button" disabled={busy || !archived} onClick={() => {setArchived(false); setOffset(0);}}>{c.activeHistory}</button>
      <button type="button" disabled={busy || archived} onClick={() => {setArchived(true); setOffset(0);}}>{c.archivedHistory}</button>
      <button type="button" disabled={busy} onClick={() => {setRefresh(n => n + 1); onChange();}}>{c.refreshHistory}</button>
    </div>
    {page?.drafts.map(row => <article key={row.id}>
      <p><code>{row.id}</code> · {row.packet} · {row.request_id}</p><p>{row.correction.slice(0, 160) || row.before.slice(0, 160)}</p>
      <div className="correction-actions">
        <button type="button" disabled={busy} onClick={() => onView(row, archived)}>{c.viewRecord}</button>
        <button type="button" disabled={busy} onClick={() => void exportRow(row)}>{c.exportRecord}</button>
        <button type="button" disabled={busy} onClick={() => setPending(row)}>{archived ? c.restore : c.archive}</button>
      </div>
    </article>)}
    {page && !page.drafts.length && <p>{c.emptyHistory}</p>}
    {pending && <div role="group" aria-label={c.confirmHistory}><p><code>{pending.id}</code> · {archived ? c.restore : c.archive}</p>{!archived && <p>{c.archiveNote}</p>}<button type="button" disabled={busy} onClick={() => void changeHistory()}>{c.confirmHistory}</button><button type="button" disabled={busy} onClick={() => setPending(null)}>{c.cancelHistory}</button></div>}
    <div className="correction-actions"><button type="button" disabled={busy || !offset} onClick={() => setOffset(n => Math.max(0, n - 20))}>{c.previousPage}</button><button type="button" disabled={busy || !page?.has_more} onClick={() => setOffset(n => n + 20)}>{c.nextPage}</button></div>
    <label>{c.importText}<textarea value={recovery} onChange={event => setRecovery(event.target.value)} disabled={busy}/></label>
    <button type="button" disabled={busy || !recovery.trim()} onClick={() => void restoreExport()}>{c.importRecord}</button>
    <p role="status">{message}</p>
    </>}
  </details>;
}
