import { createContext, useContext, useState, type ReactNode } from 'react';
import { useI18n } from '../i18n';
import { targetCorrectionCopy } from '../targetCorrectionCopy';
import type { LiveDocuments, Snapshot } from '../types';

type Context = {snapshot:Snapshot; documents:LiveDocuments|null; drafts:Map<string,string>; setDraft:(key:string,text:string)=>void};
const TargetContext = createContext<Context|null>(null);
export function TargetCorrectionProvider({snapshot,documents,children}:{snapshot:Snapshot;documents:LiveDocuments|null;children:ReactNode}) {
  const [drafts,setDrafts] = useState(new Map<string,string>());
  function setDraft(key:string,text:string) {setDrafts(current=>new Map(current).set(key,text));}
  return <TargetContext.Provider value={{snapshot,documents,drafts,setDraft}}>{children}</TargetContext.Provider>;
}
export function TargetCorrection({source,before}:{source:string;before:string}) {
  const context = useContext(TargetContext);
  if (!context) return null;
  const path = source.split('#')[0].replace(/:\d+$/, '');
  const doc = context.documents?.project_root === context.snapshot.project.root ? context.documents.documents.find(d => d.path === path) : undefined;
  const key = JSON.stringify([context.snapshot.project.root,context.snapshot.state.active_packet?.id,source,before,doc?.sha256 ?? doc?.content]);
  return <ItemCorrection key={key} context={context} draftKey={key} source={source} before={before}/>;
}
function ItemCorrection({context,draftKey,source,before}:{context:Context;draftKey:string;source:string;before:string}) {
  const {locale} = useI18n(); const c = targetCorrectionCopy[locale];
  const {snapshot,documents,drafts} = context;
  const text = drafts.get(draftKey) ?? '';
  const [result,setResult] = useState<'copied'|'error'|null>(null);
  const [busy,setBusy] = useState(false);
  const path = source.split('#')[0].replace(/:\d+$/, '');
  const doc = documents?.project_root === snapshot.project.root ? documents.documents.find(d => d.path === path) : undefined;
  const available = snapshot.inspection_status !== 'stale' && !!snapshot.state.active_packet && !!doc?.exists && doc.content !== null && !doc.error && !doc.truncated;
  const requestText = [c.instruction,`${c.project}: ${snapshot.project.root}`,`${c.packet}: ${snapshot.state.active_packet?.id ?? ''}`,
    `${c.source}: ${source}`,`${c.observed}: ${documents?.read_at ?? ''}`, ...(doc?.sha256 ? [`SHA-256: ${doc.sha256}`] : []),
    `${c.before}:\n${before}`,`${c.change}:\n${text}`].join('\n\n');
  async function copy() {
    if (!available || !text.trim() || busy) return;
    setBusy(true); setResult(null);
    try {await navigator.clipboard.writeText(requestText); setResult('copied');}
    catch {setResult('error');} finally {setBusy(false);}
  }
  return <details className="target-correction">
    <summary>{c.open}</summary>
    <div className="target-correction-body">
      <p className="interaction-meta">{c.source}: <code>{source}</code></p>
      <label>{c.edit}<textarea maxLength={4000} value={text} readOnly={busy} onChange={e => {context.setDraft(draftKey,e.target.value);setResult(null);}}/></label>
      <button type="button" disabled={!available || !text.trim() || busy} onClick={() => void copy()}>{c.copy}</button>
      {!available && <p role="status">{c.unavailable}</p>}
      <p>{c.note}</p>
      <details><summary>{c.preview}</summary><pre>{requestText}</pre></details>
      <p role="status">{result ? c[result] : ''}</p>
    </div>
  </details>;
}
