import { useEffect, useRef, useState } from "react";
import { getVerificationReceiptList, inspectVerificationReceipt, revealPath } from "../api";
import { useI18n } from "../i18n";
import { formatAbsolute } from "../time";
import type { Snapshot } from "../types";
import type { VerificationReceiptInspection, VerificationReceiptList } from "../verificationReceipts";
import { verificationCopy } from "../verificationCopy";
import "./VerificationRecords.css";

function Records({ snapshot }: { snapshot: Snapshot }) {
  const { locale } = useI18n();
  const c = verificationCopy[locale];
  const [records, setRecords] = useState<VerificationReceiptList | null>(null);
  const [selected, setSelected] = useState<VerificationReceiptInspection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const selectedPanel = useRef<HTMLElement>(null);
  useEffect(() => () => { generation.current += 1; }, []);
  useEffect(() => { if (selected) selectedPanel.current?.focus(); }, [selected]);
  const eligible = snapshot.inspection_status === "completed";
  const entry = selected?.observation;
  const packet = snapshot.state.active_packet?.id ?? null;
  function belongs(result: { version: number; project_root: string; packet: string | null }) {
    return result.version === 1 && result.project_root === snapshot.project.root && result.packet === packet;
  }
  function failure(reason: unknown) {
    const code = (reason as { code?: string } | null)?.code;
    if (code === "receipt_navigation_changed" || code === "receipt_navigation_unregistered") return c.listChanged;
    if (code === "receipt_navigation_project") return c.wrongProject;
    if (code === "receipt_navigation_unavailable") return c.listUnavailable;
    return reason instanceof Error ? reason.message : c.failedLoad;
  }
  async function read(offset = 0, revision?: string) {
    const request = ++generation.current;
    setBusy(true); setError(""); setSelected(null); setRecords(null);
    try {
      const result = await getVerificationReceiptList(snapshot.project.root, offset, revision);
      if (generation.current !== request) return;
      if (!belongs(result) || result.offset !== offset || (revision && result.revision !== revision)) throw new Error(c.wrongProject);
      setRecords(result);
    } catch (reason) {
      if (generation.current === request) setError(failure(reason));
    } finally { if (generation.current === request) setBusy(false); }
  }
  async function inspect(path: string) {
    if (!records?.paths.includes(path)) return;
    const request = ++generation.current;
    setBusy(true); setError(""); setSelected(null);
    try {
      const result = await inspectVerificationReceipt(snapshot.project.root, path, records.revision);
      if (generation.current !== request) return;
      if (!belongs(result) || result.revision !== records.revision || result.observation.path !== path) throw new Error(c.wrongProject);
      setSelected(result);
    } catch (reason) {
      if (generation.current === request) {
        setError(failure(reason));
        setRecords(null);
      }
    } finally { if (generation.current === request) setBusy(false); }
  }
  async function reveal(path: string) {
    const request = generation.current;
    try { await revealPath(path); } catch (reason) {
      if (request === generation.current) setError(reason instanceof Error ? reason.message : c.failedLoad);
    }
  }
  return <section className="verification-records" aria-label={c.title} aria-busy={busy}>
    <div className="section-heading-row"><h2>{c.title}</h2><button type="button" disabled={busy || !eligible} onClick={() => void read()}>{busy ? c.loading : records ? c.refresh : c.read}</button></div>
    <p>{c.note}</p>
    {!eligible && <p role="status">{c.stale}</p>}
    {error && <p role="alert">{error}</p>}
    {records && <>
      <p className="verification-observed">{c.listRead}: <time dateTime={records.read_at}>{formatAbsolute(records.read_at, locale)}</time></p>
      {!records.paths.length ? <p>{c.empty}</p> : <>
        <p>{c.choose}</p>
        <ul className="verification-list">{records.paths.map(path => <li key={path}>
          <button type="button" className="verification-path" disabled={busy || !eligible} aria-pressed={entry?.path === path} aria-label={`${c.inspect}: ${path}`} onClick={() => void inspect(path)}>
            <code>{path}</code><span>{c.inspect}</span>
          </button>
        </li>)}</ul>
        <nav className="verification-pagination" aria-label={c.pages}>
          <button type="button" disabled={busy || records.offset === 0} onClick={() => void read(Math.max(0, records.offset - 10), records.revision)}>{c.previous}</button>
          <span role="status">{records.offset + 1}–{records.offset + records.paths.length} / {records.total}</span>
          <button type="button" disabled={busy || records.next_offset === null} onClick={() => records.next_offset !== null && void read(records.next_offset, records.revision)}>{c.next}</button>
        </nav>
      </>}
    </>}
    <details className="verification-connection"><summary>{c.connection}</summary>
      <p>{c.connectionNote}</p>
      <code className="verification-command">{'python scripts/sdad_evidence.py --project "PROJECT" --preview-connection "path/to/receipt.json"'}</code>
    </details>
    {entry && selected && <article className="verification-selected" aria-label={c.selected} ref={selectedPanel} tabIndex={-1}>
      <div className="section-heading-row"><h3>{c.selected}</h3><button type="button" disabled={busy || !eligible} onClick={() => void inspect(entry.path)}>{c.compareAgain}</button></div>
      <button type="button" className="verification-source-path" onClick={() => void reveal(entry.path)} title={c.openReceipt}>{entry.path}</button>
      <p className="verification-observed">{c.observed}: <time dateTime={selected.read_at}>{formatAbsolute(selected.read_at, locale)}</time></p>
      {entry.error && <p role="alert">{entry.error}</p>}
      {entry.receipt && <>
        <div className="verification-badges"><strong>{c[entry.receipt.outcome]}</strong><span>{entry.receipt.packet === packet ? c.current : c.historical}: {entry.receipt.packet}</span></div>
        <p><strong>{c.requirement}:</strong> {entry.receipt.requirement}</p><p><strong>{c.scope}:</strong> {entry.receipt.scope}</p>
        <div className="verification-badges"><span>{c.source}: {c[entry.source_match]}</span><span>{c.log}: {c[entry.log_match]}</span></div>
        <p>{c.ran}: <time dateTime={entry.receipt.ended_at}>{formatAbsolute(entry.receipt.ended_at, locale)}</time> · {c.exit}: {entry.receipt.exit_code ?? "—"}</p>
        {entry.receipt.source_stability !== "stable" && <p role="status">{entry.receipt.source_stability === "changed" ? c.duringRun : c.unknownRun}</p>}
        <details><summary>{c.details}</summary>
          <code className="verification-command">{JSON.stringify(entry.receipt.command.argv)}</code>
          <ul>{entry.sources.map(source => <li key={source.path}><code>{source.path}</code> — {c[source.match]}{source.reason && <small>{source.reason}</small>}</li>)}</ul>
          <p>{c.retained}: {entry.receipt.log.bytes} · {c.total}: {entry.receipt.log.total_bytes}</p>
          {entry.receipt.log.truncated && <p>{c.logPartial}</p>}
          {!entry.receipt.log.complete && <p role="status">{c.logIncomplete}</p>}
          <button type="button" onClick={() => void reveal(entry.receipt!.log.path)}>{c.openLog}</button>
          {entry.receipt.limits.length > 0 && <ul>{entry.receipt.limits.map((limit, index) => <li key={index}>{limit}</li>)}</ul>}
        </details>
        <p className="verification-limit">{c.notProof}</p>
      </>}
    </article>}
  </section>;
}

export function VerificationRecords({ snapshot }: { snapshot: Snapshot }) {
  return <Records key={`${snapshot.project.identity}:${snapshot.inspection_id}:${snapshot.inspection_status}`} snapshot={snapshot} />;
}
