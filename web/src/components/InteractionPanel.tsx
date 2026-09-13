import { useEffect, useState } from 'react';
import { getCorrections, saveCorrection } from '../api';
import { useI18n } from '../i18n';
import { interactionCopy, type InteractionCopy } from '../interactionCopy';
import { correctionParent, correctionText, responseState, type Correction, type InteractionRecord } from '../interactions';
import { documentSelectionId } from '../selection';
import type { LiveDocuments, Snapshot } from '../types';

function RecordView({record: r, copy: c, documents, snapshot, onSelect}: {record: InteractionRecord; copy: InteractionCopy; documents: LiveDocuments; snapshot: Snapshot; onSelect: (id: string) => void}) {
  return <article className="interaction-report">
    <header><strong>{c[r.kind]}</strong><span>{r.link_status === 'matched' ? (r.kind === 'request' ? c.userSource : c.report) : r.link_status === 'stale' ? c.stale : r.link_status === 'conflict' ? c.conflict : c.unknown}</span></header>
    <p>{r.summary}</p>{r.result_revision && <p className="interaction-meta">{c.revision}: {r.base_revision} → {r.result_revision}</p>}
    {r.source_ref && <p><small>{c.userSource}: {r.source_ref}</small></p>}
    {(['scope','excluded','assumptions','remaining','impact','alternatives'] as const).map(key => r[key]?.length ? <div key={key}><strong>{c[key]}</strong><ul>{r[key]!.map((text,index) => <li key={index}>{text}</li>)}</ul></div> : null)}
    {(['reason','owner_question'] as const).map(key => r[key] ? <p key={key}><strong>{c[key]}: </strong>{r[key]}</p> : null)}
    {r.criteria?.map(item => <p key={item.id}><strong>{item.id}</strong> {item.summary} <em>{item.status === 'remaining' ? c.remainingStatus : item.status === 'blocked' ? c.blocked : item.status === 'implemented_reported' ? c.implemented : c.verification_reported}</em></p>)}
    {!!r.evidence?.length && <div><strong>{c.evidence}</strong>{r.evidence.map((e,index) => {
      const path = e.path.split('#')[0]; const available = documents.documents.some(d => d.path === path && d.content !== null && !d.error);
      return <p key={index}>{e.result} <button type="button" disabled={!available} title={!available ? c.unavailable : e.path} onClick={() => onSelect(documentSelectionId(snapshot, path))}>{e.path}</button></p>;
    })}</div>}
    <footer><small>{r.author} · {r.reported_at}</small><button type="button" onClick={() => onSelect(documentSelectionId(snapshot, r.source.path))}>{c.source} · {r.source.path}:{r.source.line}</button></footer>
  </article>;
}

// Page-session memory only. Explicit Save/Copy remains the reload boundary.
const sessions = new Map<string, {requestId: string; drafts: Map<string, Correction>}>();
export function clearCorrectionSessions() { sessions.clear(); }
type Props = {snapshot: Snapshot; documents: LiveDocuments | null; onSelect: (id: string) => void};
export function InteractionPanel(props: Props) {
  return <ProjectInteractionPanel key={props.snapshot.project.root} {...props}/>;
}
function ProjectInteractionPanel({snapshot, documents, onSelect}: Props) {
  const {locale} = useI18n(); const c = interactionCopy[locale];
  const [session] = useState(() => {
    let value = sessions.get(snapshot.project.root);
    if (!value) {value = {requestId:'',drafts:new Map()}; sessions.set(snapshot.project.root,value);}
    return value;
  });
  const [,refreshSession] = useState(0);
  const requestId = session.requestId;
  function setRequestId(value: string) {session.requestId = value; refreshSession(n => n+1);}
  const [drafts,setDrafts] = useState<Correction[]>([]);
  const [historyReady,setHistoryReady] = useState(false);
  const [message,setMessage] = useState(''); const [busy,setBusy] = useState(false);
  const projection = documents?.project_root === snapshot.project.root ? documents.interactions : undefined;
  const supported = projection?.schema_version === 1 && projection.packet === snapshot.state.active_packet?.id;
  const records = supported ? projection.records : [];
  const requests = records.filter(r => r.kind === 'request' && r.link_status === 'matched');
  const request = requests.find(r => r.request_id === requestId) ?? requests[0];
  const related = records.filter(r => r.request_id === request?.request_id && r.packet === request?.packet);
  const interpretation = related.find(r => r.kind === 'interpretation' && r.link_status === 'matched');
  const incomplete = !supported || projection.status === 'incomplete' || snapshot.inspection_status === 'stale';
  const targetDrafts = drafts.filter(d => d.request_id === request?.request_id && d.packet === request?.packet);
  const targetKey = JSON.stringify([request?.packet,request?.request_id]);
  const draft = session.drafts.get(targetKey) ?? null;
  function setDraft(value: Correction) {session.drafts.set(targetKey,value); refreshSession(n => n+1);}
  function rememberSaved(saved: Correction) {
    setDraft(saved);
    setDrafts(rows => rows.some(r => r.id === saved.id) ? rows.map(r => r.id === saved.id ? saved : r) : [...rows,saved]);
  }
  useEffect(() => {
    let active = true;
    getCorrections().then(value => {if (active && value.project_root === snapshot.project.root && Array.isArray(value.drafts)) {setDrafts(value.drafts); setHistoryReady(true);}}).catch(() => {if(active) setMessage(c.error);});
    return () => {active = false;};
  }, [snapshot.project.root]); // No independent polling; reports use the existing workspace refresh.
  function createDraft() {
    if (!request || !interpretation) return;
    const previous = correctionParent(targetDrafts, draft);
    setDraft({id: `correction-${crypto.randomUUID()}`, project_root: snapshot.project.root, packet: request.packet, request_id: request.request_id,
      base_revision: request.base_revision, before: interpretation.summary, correction: '', supersedes: previous, copy_state: 'draft'});
    setMessage('');
  }
  function recoverDraft() {
    if (!draft || !request || !interpretation) return;
    setDraft({...draft, id:`correction-${crypto.randomUUID()}`, revision:0,
      base_revision:request.base_revision, before:interpretation.summary,
      supersedes:targetDrafts.some(d => d.id === draft.id) ? draft.id : draft.supersedes, copy_state:'draft'});
    setMessage('');
  }
  async function persist(copy: boolean) {
    if (!draft) return;
    setBusy(true); setMessage('');
    try {
      let saved = await saveCorrection(copy && draft.copy_state === 'draft' ? {...draft, copy_state:'sealed'} : draft);
      // Seal identity before touching the clipboard: a later storage failure must
      // never allow different text to reuse an already exposed correction ID.
      rememberSaved(saved);
      if (copy) {await navigator.clipboard.writeText(correctionText(saved)); saved = await saveCorrection({...saved, copy_state:'copied'});}
      rememberSaved(saved); setMessage(copy ? c.copied : c.saved);
    } catch {setMessage(c.error);} finally {setBusy(false);}
  }
  return <section className="interaction-panel" aria-labelledby="interaction-heading">
    <h2 id="interaction-heading">{c.title}</h2>
    {!requests.length ? <p>{c.empty}</p> : <>
      <label>{c.request}<select disabled={busy} value={request?.request_id} onChange={e => {setRequestId(e.target.value);setMessage('');}}>{requests.map(r => <option key={r.id} value={r.request_id}>{r.summary}</option>)}</select></label>
      <p className="interaction-meta">{c.revision}: <code>{request.base_revision}</code> · {c.observed}: {projection?.observed_at}</p>
      <div className="interaction-comparison"><RecordView record={request} copy={c} documents={documents!} snapshot={snapshot} onSelect={onSelect}/>
      {interpretation ? <RecordView record={interpretation} copy={c} documents={documents!} snapshot={snapshot} onSelect={onSelect}/> : <p>{c.noInterpretation}</p>}</div>
      {related.filter(r => ['progress','decision'].includes(r.kind) && r.link_status !== 'superseded').map(r => <RecordView key={`${r.id}:${r.source.path}:${r.source.line}`} record={r} copy={c} documents={documents!} snapshot={snapshot} onSelect={onSelect}/>)}
      <button type="button" onClick={createDraft} disabled={!historyReady || !interpretation || incomplete || busy || draft?.copy_state === 'draft'}>{targetDrafts.length ? c.next : c.correct}</button>
      <p>{c.note}</p>
      {targetDrafts.length > 0 && <div className="correction-history"><strong>{c.history}</strong>{targetDrafts.map(d => <button key={d.id} type="button" disabled={busy || draft?.copy_state === 'draft'} onClick={() => {setDraft(d);setMessage('');}}>{d.correction.slice(0,80) || d.id} · {c[responseState(d,records,incomplete,request.base_revision) as keyof InteractionCopy]}</button>)}</div>}
      {draft && draft.request_id === request.request_id && <div className="correction-composer">
        <small><code>{draft.id}</code> · {c[responseState(draft,records,incomplete,request.base_revision) as keyof InteractionCopy]}</small>
        <label>{c.correction}<textarea value={draft.correction} maxLength={4000} readOnly={busy || draft.copy_state !== 'draft'} onChange={e => setDraft({...draft,correction:e.target.value})}/></label>
        <p>{draft.copy_state === 'draft' ? c.savedOnly : c[draft.copy_state]}</p><div className="correction-actions"><button type="button" disabled={busy || draft.copy_state !== 'draft'} onClick={() => void persist(false)}>{c.save}</button><button type="button" disabled={busy || !draft.correction.trim() || incomplete || draft.base_revision !== request.base_revision} onClick={() => void persist(true)}>{c.copy}</button></div>
        {(message === c.error || draft.base_revision !== request.base_revision) && <p>{c.recoveryHint} <button type="button" disabled={busy || !interpretation || incomplete} onClick={recoverDraft}>{c.recover}</button></p>}
        <details><summary>{c.preview}</summary><pre>{correctionText(draft)}</pre></details>
        {related.filter(r => r.kind === 'response' && r.correction_id === draft.id).map(r => <RecordView key={`${r.id}:${r.source.path}:${r.source.line}`} record={r} copy={c} documents={documents!} snapshot={snapshot} onSelect={onSelect}/>)}
      </div>}
    </>}
    {(incomplete && supported || records.some(r => ['conflict','stale'].includes(r.link_status))) && <p role="status">{c.warning}</p>}
    {projection?.issues.map((issue,index) => <p className="interaction-meta" key={index}>{issue.path}:{issue.line} · {issue.code}</p>)}
    <p role="status">{message}</p>
  </section>;
}
