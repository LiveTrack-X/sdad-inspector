import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { getVerificationReceiptList, inspectVerificationReceipt, revealPath } from "../api";
import { useI18n } from "../i18n";
import { formatAbsolute } from "../time";
import type { Snapshot } from "../types";
import type { VerificationReceiptInspection, VerificationReceiptList } from "../verificationReceipts";
import { verificationCopy } from "../verificationCopy";
import { explainVerificationReason } from "../verificationDetails";
import "./VerificationRecords.css";

function Records({ snapshot }: { snapshot: Snapshot }) {
  const { locale } = useI18n();
  const c = verificationCopy[locale];
  const [records, setRecords] = useState<VerificationReceiptList | null>(null);
  const [selected, setSelected] = useState<VerificationReceiptInspection | null>(null);
  const [compared, setCompared] = useState<VerificationReceiptInspection[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rawError, setRawError] = useState("");
  const generation = useRef(0);
  const selectedPanel = useRef<HTMLElement>(null);
  const comparisonPanel = useRef<HTMLDivElement>(null);
  useEffect(() => () => { generation.current += 1; }, []);
  useEffect(() => { if (selected) (compared.length === 2 ? comparisonPanel.current : selectedPanel.current)?.focus(); }, [selected]);
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
  function reportFailure(reason: unknown) {
    setError(failure(reason));
    const code = (reason as { code?: unknown } | null)?.code;
    setRawError(typeof code === "string" ? JSON.stringify({ code, message: reason instanceof Error ? reason.message : null }) : "");
  }
  async function read(offset = 0, revision?: string) {
    const request = ++generation.current;
    setBusy(true); setError(""); setRawError(""); setSelected(null); setRecords(null);
    // Paging one pinned route list retains observations; an explicit fresh read
    // starts a new comparison, even when the server returns the same revision.
    if (!revision) setCompared([]);
    try {
      const result = await getVerificationReceiptList(snapshot.project.root, offset, revision);
      if (generation.current !== request) return;
      if (!belongs(result) || result.offset !== offset || (revision && result.revision !== revision)) throw new Error(c.wrongProject);
      setRecords(result);
    } catch (reason) {
      if (generation.current === request) { reportFailure(reason); setCompared([]); }
    } finally { if (generation.current === request) setBusy(false); }
  }
  async function inspect(path: string) {
    if (!records?.paths.includes(path)) return;
    const request = ++generation.current;
    setBusy(true); setError(""); setRawError(""); setSelected(null);
    setCompared(previous => previous.filter(item => item.observation.path !== path));
    try {
      const result = await inspectVerificationReceipt(snapshot.project.root, path, records.revision);
      if (generation.current !== request) return;
      if (!belongs(result) || result.revision !== records.revision || result.observation.path !== path) throw new Error(c.wrongProject);
      setSelected(result);
      setCompared(previous => [...previous.filter(item => item.observation.path !== path), result].slice(-2));
    } catch (reason) {
      if (generation.current === request) {
        reportFailure(reason);
        setRecords(null);
        setCompared([]);
      }
    } finally { if (generation.current === request) setBusy(false); }
  }
  async function reveal(path: string) {
    const request = generation.current;
    try { await revealPath(path); } catch (reason) {
      if (request === generation.current) reportFailure(reason);
    }
  }
  const comparisonRows: Array<{ label: string; value: (item: VerificationReceiptInspection) => ReactNode }> = [
    { label: c.packetLabel, value: item => item.observation.receipt ? <>{item.observation.receipt!.packet}<small>{item.observation.receipt!.packet === packet ? c.current : c.historical}</small></> : c.unknown },
    { label: c.requirement, value: item => item.observation.receipt?.requirement ?? c.unknown },
    { label: c.scope, value: item => item.observation.receipt?.scope ?? c.unknown },
    { label: c.outcomeLabel, value: item => item.observation.receipt ? <>{c[item.observation.receipt!.outcome]}<small>{c.exit}: {item.observation.receipt!.exit_code ?? c.notRecorded}</small></> : c.unknown },
    { label: c.source, value: item => <>{c[item.observation.source_match]}{item.observation.receipt?.source_stability === "changed" && <small>{c.duringRun}</small>}{item.observation.receipt?.source_stability === "unknown" && <small>{c.unknownRun}</small>}</> },
    { label: c.log, value: item => <>{c[item.observation.log_match]}{item.observation.receipt?.log.truncated && <small>{c.logPartial}</small>}{item.observation.receipt && !item.observation.receipt.log.complete && <small>{c.logIncomplete}</small>}</> },
    { label: c.ran, value: item => item.observation.receipt ? <time dateTime={item.observation.receipt.ended_at}>{formatAbsolute(item.observation.receipt.ended_at, locale)}</time> : c.notRecorded },
    { label: c.observed, value: item => <time dateTime={item.read_at}>{formatAbsolute(item.read_at, locale)}</time> },
  ];
  return <section className="verification-records" aria-label={c.title} aria-busy={busy}>
    <div className="section-heading-row"><h2>{c.title}</h2><button type="button" disabled={busy || !eligible} onClick={() => void read()}>{busy ? c.loading : records ? c.refresh : c.read}</button></div>
    <p>{c.note}</p>
    {!eligible && <p role="status">{c.stale}</p>}
    {error && <p role="alert">{error}</p>}
    {rawError && <details><summary>{c.errorDetails}</summary><code className="verification-command">{rawError}</code></details>}
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
    {compared.length > 0 && <section className="verification-comparison" aria-label={c.comparison}>
      <div className="section-heading-row"><h3>{c.comparison}</h3><button type="button" disabled={busy} onClick={() => setCompared([])}>{c.clearComparison}</button></div>
      {compared.length === 1 ? <p><code>{compared[0].observation.path}</code> · {c.comparisonHint}</p> : <>
        <p>{c.comparisonNote}</p>
        <p className="verification-comparison-scroll-hint">{c.comparisonScroll}</p>
        <div className="verification-comparison-scroll" ref={comparisonPanel} tabIndex={0} role="region" aria-label={c.comparison}>
          <table aria-label={c.comparison}>
            <thead><tr><th scope="col">{c.recordField}</th>{compared.map(item => <th scope="col" key={item.observation.path}>
              <code>{item.observation.path}</code><button type="button" disabled={busy} aria-label={`${c.removeComparison}: ${item.observation.path}`} onClick={() => setCompared(previous => previous.filter(record => record.observation.path !== item.observation.path))}>{c.removeComparison}</button>
            </th>)}</tr></thead>
            <tbody>{comparisonRows.map(row => <tr key={row.label}><th scope="row">{row.label}</th>{compared.map(item => <td key={item.observation.path}>{row.value(item)}</td>)}</tr>)}
              {compared.some(item => item.observation.error) && <tr><th scope="row">{c.errorDetails}</th>{compared.map(item => <td key={item.observation.path}>{item.observation.error ?? c.notRecorded}</td>)}</tr>}
              <tr><th scope="row">{c.rawEvidence}</th>{compared.map(item => <td key={item.observation.path}><details><summary>{c.rawEvidence}</summary><pre>{JSON.stringify(item, null, 2)}</pre></details></td>)}</tr>
            </tbody>
          </table>
        </div>
      </>}
    </section>}
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
          <h4>{c.commandLabel}</h4>
          <code className="verification-command">{JSON.stringify(entry.receipt.command.argv)}</code>
          <h4>{c.sourceDetails}</h4>
          <ul>{entry.sources.map(source => <li key={source.path}><code>{source.path}</code> — {c[source.match]}{source.reason && <>
            <p>{explainVerificationReason(source.reason, c)}</p><details><summary>{c.rawReason}</summary><code className="verification-command">{source.reason}</code></details>
          </>}</li>)}</ul>
          <h4>{c.captureLabel}</h4>
          <p>{c.retained}: {entry.receipt.log.bytes} · {c.total}: {entry.receipt.log.total_bytes}</p>
          {entry.receipt.log.truncated && <p>{c.logPartial}</p>}
          {!entry.receipt.log.complete && <p role="status">{c.logIncomplete}</p>}
          <button type="button" onClick={() => void reveal(entry.receipt!.log.path)}>{c.openLog}</button>
          {entry.receipt.limits.length > 0 && <><h4>{c.originalLimits}</h4><ul>{entry.receipt.limits.map((limit, index) => <li key={index}>{limit}</li>)}</ul></>}
        </details>
        <p className="verification-limit">{c.notProof}</p>
      </>}
      <details className="verification-raw"><summary>{c.rawEvidence}</summary><pre>{JSON.stringify(selected, null, 2)}</pre></details>
    </article>}
  </section>;
}

export function VerificationRecords({ snapshot }: { snapshot: Snapshot }) {
  const context = JSON.stringify([snapshot.project.identity, snapshot.project.root, snapshot.inspection_id,
    snapshot.inspection_status, snapshot.state.active_packet?.id, snapshot.state.routed_docs]);
  return <Records key={context} snapshot={snapshot} />;
}
