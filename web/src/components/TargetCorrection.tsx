import { createContext, useContext, useState, type ReactNode } from 'react';
import { useI18n } from '../i18n';
import { targetCorrectionCopy } from '../targetCorrectionCopy';
import type { LiveDocuments, Snapshot } from '../types';

type Draft = {target:string; documentScope:string; source:string; before:string; revision:string; observed:string; text:string};
type Context = {snapshot:Snapshot; documents:LiveDocuments|null; drafts:Map<string,Draft>; setDraft:(key:string,draft:Draft)=>void};
const TargetContext = createContext<Context|null>(null);
export function TargetCorrectionProvider({snapshot,documents,children}:{snapshot:Snapshot;documents:LiveDocuments|null;children:ReactNode}) {
  const [drafts,setDrafts] = useState(new Map<string,Draft>());
  function setDraft(key:string,draft:Draft) {setDrafts(current=>new Map(current).set(key,draft));}
  return <TargetContext.Provider value={{snapshot,documents,drafts,setDraft}}>{children}</TargetContext.Provider>;
}
export function TargetCorrection({source,before}:{source:string;before:string}) {
  const context = useContext(TargetContext);
  if (!context) return null;
  const path = source.split('#')[0].replace(/:\d+$/, '');
  const doc = context.documents?.project_root === context.snapshot.project.root ? context.documents.documents.find(d => d.path === path) : undefined;
  const target = JSON.stringify([context.snapshot.project.root,context.snapshot.state.active_packet?.id,source]);
  const documentScope = JSON.stringify([context.snapshot.project.root,context.snapshot.state.active_packet?.id,path]);
  const key = JSON.stringify([target,before,doc?.sha256 ?? doc?.content]);
  return <ItemCorrection key={key} context={context} target={target} documentScope={documentScope} draftKey={key} source={source} before={before}/>;
}
function ItemCorrection({context,target,documentScope,draftKey,source,before}:{context:Context;target:string;documentScope:string;draftKey:string;source:string;before:string}) {
  const {locale} = useI18n(); const c = targetCorrectionCopy[locale];
  const {snapshot,documents,drafts} = context;
  const text = drafts.get(draftKey)?.text ?? '';
  const previous = [...drafts.entries()].filter(([key,draft]) => key !== draftKey && draft.target === target && draft.text.trim()).reverse();
  const otherLocations = [...drafts.entries()].filter(([,draft]) => draft.documentScope === documentScope && draft.target !== target && draft.text.trim()).reverse();
  const [result,setResult] = useState<'copied'|'error'|null>(null);
  const [busy,setBusy] = useState(false);
  const path = source.split('#')[0].replace(/:\d+$/, '');
  const doc = documents?.project_root === snapshot.project.root ? documents.documents.find(d => d.path === path) : undefined;
  const available = snapshot.inspection_status !== 'stale' && snapshot.state.available && !!snapshot.state.active_packet && !!doc?.exists && doc.content !== null && !doc.error && !doc.truncated;
  function setText(value:string) {
    context.setDraft(draftKey,{target,documentScope,source,before,revision:doc?.sha256 ?? '',observed:documents?.read_at ?? '',text:value});
    setResult(null);
  }
  const requestText = [c.instruction,`${c.project}: ${snapshot.project.root}`,`${c.packet}: ${snapshot.state.active_packet?.id ?? ''}`,
    `${c.source}: ${source}`,`${c.observed}: ${documents?.read_at ?? ''}`, ...(doc?.sha256 ? [`SHA-256: ${doc.sha256}`] : []),
    `${c.before}:\n${before}`,`${c.change}:\n${text}`].join('\n\n');
  async function copy() {
    if (!available || !text.trim() || busy) return;
    setBusy(true); setResult(null);
    try {await navigator.clipboard.writeText(requestText); setResult('copied');}
    catch {setResult('error');} finally {setBusy(false);}
  }
  function draftComparison([key,draft]:[string,Draft],index:number) {
    return <details key={key}>
      <summary>{c.previousDrafts} {index + 1} · {draft.observed}</summary>
      <p>{c.previousSource}: <code>{draft.source}</code></p><pre>{draft.before}</pre>
      {draft.revision && <p>SHA-256: <code>{draft.revision}</code></p>}
      <p>{c.currentSource}: <code>{source}</code></p><pre>{before}</pre>
      {doc?.sha256 && <p>SHA-256: <code>{doc.sha256}</code></p>}
      <p>{c.observed}: {documents?.read_at ?? ''}</p>
      <p>{draft.source !== source ? c.locationChanged : draft.before === before ? c.itemUnchanged : c.itemChanged}</p>
      <p>{c.previousText}</p><pre>{draft.text}</pre>
      <button type="button" disabled={!available || busy || !!text} onClick={() => setText(draft.text)}>{c.usePrevious}</button>
      {!!text && <p>{c.keepCurrent}</p>}
    </details>;
  }
  return <details className="target-correction">
    <summary>{c.open}</summary>
    <div className="target-correction-body">
      <p className="interaction-meta">{c.source}: <code>{source}</code></p>
      {previous.length > 0 && <section aria-label={c.previousDrafts}>
        <p>{c.recoveryNotice}</p>
        {previous.map(draftComparison)}
      </section>}
      {otherLocations.length > 0 && <details>
        <summary>{c.documentDrafts}</summary>
        <section aria-label={c.documentDrafts}>
          <p>{c.documentRecoveryNotice}</p>
          {otherLocations.map(draftComparison)}
        </section>
      </details>}
      <label>{c.edit}<textarea maxLength={4000} value={text} readOnly={busy} onChange={e => setText(e.target.value)}/></label>
      <button type="button" disabled={!available || !text.trim() || busy} onClick={() => void copy()}>{c.copy}</button>
      {!available && <p role="status">{c.unavailable}</p>}
      <p>{c.note}</p>
      <details><summary>{c.preview}</summary><pre>{requestText}</pre></details>
      <p role="status">{result ? c[result] : ''}</p>
    </div>
  </details>;
}
