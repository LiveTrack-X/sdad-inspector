import { ArrowSquareOut, CaretDown } from '@phosphor-icons/react';
import { useI18n } from '../i18n';
import type { PacketWorkItem } from '../packetWork';
import { documentSelectionId } from '../selection';
import type { LiveDocument, LiveDocuments, Snapshot } from '../types';
import { workDetailCopy } from '../workDetailCopy';
import { MarkdownViewer } from './MarkdownViewer';
import { TargetCorrection } from './TargetCorrection';

export function WorkItemDetails({item, todoPath, onOpenSource}: {item: PacketWorkItem; todoPath: string; onOpenSource: () => void}) {
  const {locale} = useI18n(); const c = workDetailCopy[locale];
  const excerpt: LiveDocument = {path:todoPath, exists:true, roles:['todo'], content:item.detail ?? item.text, error:null};
  return <details className="work-item-details">
    <summary><span>{item.summary ?? item.text}</span><CaretDown size={16} aria-hidden="true"/></summary>
    <div className="work-item-detail-body">
      <strong>{c.taskDetails}</strong>
      <MarkdownViewer document={excerpt}/>
      <dl>
        <dt>{c.status}</dt><dd>{item.completed ? c.checked : item.current ? c.current : c.remaining}</dd>
        <dt>{c.phase}</dt><dd>{item.phaseConflict ? c.conflict : item.phase ?? c.unknown}</dd>
        <dt>{c.section}</dt><dd>{item.section}</dd>
      </dl>
      <button type="button" className="work-source-action" onClick={onOpenSource}>{c.openSource}<ArrowSquareOut size={16}/></button>
      <small>{c.source}: <code>{todoPath}{item.line ? `:${item.line}` : ''}</code></small>
      <TargetCorrection source={`${todoPath}${item.line ? `:${item.line}` : ''}`} before={item.detail ?? item.text}/>
    </div>
  </details>;
}

export function PlanDetails({snapshot, documents, work, onSelect}: {snapshot:Snapshot; documents:LiveDocuments|null; work:PacketWorkItem[]; onSelect:(id:string)=>void}) {
  const {locale} = useI18n(); const c = workDetailCopy[locale];
  const sameProject = documents?.project_root === snapshot.project.root;
  const available = sameProject ? documents.documents : [];
  const planWork = sameProject ? work.filter(item => item.phase === 'plan' && !item.phaseConflict && !item.completed) : [];
  // A route makes a document available; it does not make it an AI plan or authority.
  const eligible = new Set([snapshot.protocol.state_path, snapshot.protocol.todo_path, snapshot.state.active_spec?.path, ...snapshot.state.routed_docs]);
  const connected = available.filter(doc => eligible.has(doc.path));
  return <section className="plan-detail-panel" aria-label={c.plan}>
    <h3>{c.plan}</h3>
    <p className="detail-note">{c.planNote}</p>
    {(!sameProject || snapshot.inspection_status === 'stale') && <p role="status">{c.stale}</p>}
    <h4>{c.objective}</h4><p>{snapshot.state.active_packet?.objective ?? c.unknown}</p>
    {snapshot.state.active_packet?.objective && <TargetCorrection source={`${snapshot.protocol.state_path}#active_packet.objective`} before={snapshot.state.active_packet.objective}/>}
    <h4>{c.planWork}</h4>
    {planWork.length ? <ul className="plan-task-list">{planWork.map((item,index) => <li key={index}><WorkItemDetails item={item} todoPath={snapshot.protocol.todo_path} onOpenSource={() => onSelect(documentSelectionId(snapshot,snapshot.protocol.todo_path))}/></li>)}</ul> : <p>{c.noPlanWork}</p>}
    <h4>{c.documents}</h4>
    {!connected.length && <p>{c.noDocuments}</p>}
    <div className="plan-source-list">{connected.map(doc => <details key={doc.path}>
      <summary><code>{doc.path}</code><CaretDown size={16} aria-hidden="true"/></summary>
      <div className="plan-source-preview"><MarkdownViewer document={doc} navigation/></div>
      <button type="button" className="work-source-action" onClick={() => onSelect(documentSelectionId(snapshot,doc.path))}>{c.openSource}<ArrowSquareOut size={16}/></button>
    </details>)}</div>
  </section>;
}
