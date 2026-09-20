import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { resumeComparisonAction } from '../api';
import { useI18n } from '../i18n';
import { compareResumeObservations, resumeObservation, resumeProject, sameResumeProject, type ResumeChange, type ResumeField, type ResumeStore } from '../resumeComparison';
import { resumeComparisonCopy, type ResumeCopy } from '../resumeComparisonCopy';
import { formatAbsolute } from '../time';
import type { Snapshot } from '../types';
import './ResumeComparison.css';

function ChangeRow({ row, copy, onOpenSource }: { row: ResumeChange; copy: ResumeCopy; onOpenSource: (path: string) => void }) {
  function value(text: string | null) {
    if (text === null || text === '') return row.kind === 'source' ? copy.fieldUnknown : copy.none;
    return row.kind === 'source' && text === 'absent' ? copy.absent : text;
  }
  return <li className="resume-change" data-comparison={row.status}>
    <div className="resume-change-heading"><strong>{row.kind === 'field' ? copy[row.name as ResumeField] : row.name}</strong><span>{copy[row.status]}</span></div>
    <div className="resume-values">
      <div><small>{copy.baseline}</small><pre>{value(row.before)}</pre></div>
      <div><small>{copy.current}</small><pre>{value(row.after)}</pre></div>
    </div>
    <button className="resume-source" type="button" onClick={() => onOpenSource(row.sourcePath)}>{copy.source}: <code>{row.sourcePath}</code></button>
  </li>;
}

export function ResumeComparison({ snapshot, busy = false, onOpenSource }: { snapshot: Snapshot; busy?: boolean; onOpenSource: (path: string) => void }) {
  const { locale } = useI18n();
  const c = resumeComparisonCopy[locale];
  const id = useId();
  const observation = useMemo(() => resumeObservation(snapshot), [snapshot]);
  const project = useMemo(() => ({ projectIdentity: snapshot.project.identity, projectRoot: snapshot.project.root }), [snapshot.project.identity, snapshot.project.root]);
  const [history, setHistory] = useState<{ store: ResumeStore; error: boolean }>({ store: { version: 1, projects: [] }, error: false });
  const [pending, setPending] = useState(false);
  const requestSerial = useRef(0);
  const [open, setOpen] = useState(false);
  const saved = resumeProject(history.store, project);
  const newerSaved = Boolean(saved && observation && Date.parse(saved.latest.inspectedAt) > Date.parse(observation.inspectedAt));
  const changes = saved && observation && !newerSaved ? compareResumeObservations(saved.baseline, observation) : null;

  const request = useCallback(async (action: 'read' | 'enable' | 'observe' | 'replace' | 'clear' | 'clear_all') => {
    const serial = ++requestSerial.current;
    setPending(true);
    try {
      const store = await resumeComparisonAction(project.projectRoot, snapshot.inspection_id, action);
      if (serial !== requestSerial.current) return false;
      // Keep a late response or malformed projection from crossing project boundaries.
      if (store.version !== 1 || !Array.isArray(store.projects)
        || store.projects.some((entry) => !sameResumeProject(entry.baseline, project) || !sameResumeProject(entry.latest, project))) throw new Error('project mismatch');
      setHistory({ store, error: false });
      return true;
    } catch {
      if (serial === requestSerial.current) setHistory((old) => ({ ...old, error: true }));
      return false;
    } finally {
      if (serial === requestSerial.current) setPending(false);
    }
  }, [project, snapshot.inspection_id]);

  useEffect(() => { setOpen(false); }, [project]);
  useEffect(() => {
    if (!busy) void request(observation ? 'observe' : 'read');
    return () => { requestSerial.current += 1; };
  }, [observation, busy, request]);

  function save(mode: 'enable' | 'replace') {
    if (!observation || busy || pending) return;
    void request(mode);
  }
  async function clear(all = false) {
    if (await request(all ? 'clear_all' : 'clear')) setOpen(false);
  }

  return <section className="resume-comparison" aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`}>{c.title}</h2>
    <p>{c.introduction}</p>
    {!saved && <p className="resume-storage-note">{c.privacy}</p>}
    {history.error && <p role="alert">{c.storageError}</p>}
    {!observation && <p role="status">{c.unavailable}</p>}
    {newerSaved && <p role="status">{c.newerSaved}</p>}
    {saved && <>
      <p>{c.pinned}</p>
      <dl className="resume-observation-times">
        <div><dt>{c.baseline}</dt><dd><time dateTime={saved.baseline.inspectedAt}>{formatAbsolute(saved.baseline.inspectedAt, locale)}</time></dd></div>
        <div><dt>{c.latest}</dt><dd><time dateTime={saved.latest.inspectedAt}>{formatAbsolute(saved.latest.inspectedAt, locale)}</time></dd></div>
      </dl>
    </>}
    <div className="resume-actions">
      {!saved ? <button type="button" disabled={!observation || busy || pending || history.error} onClick={() => save('enable')}>{c.enable}</button>
        : <>
          <button type="button" disabled={!changes || busy || pending} aria-expanded={open} aria-controls={`${id}-changes`} onClick={() => setOpen(!open)}>{open ? c.close : c.compare}</button>
          <button type="button" disabled={!observation || newerSaved || busy || pending || history.error} onClick={() => save('replace')}>{c.replace}</button>
          <button type="button" disabled={pending || busy} onClick={() => void clear()}>{c.clear}</button>
        </>}
      {history.error && <button type="button" disabled={pending || busy} onClick={() => void request('read')}>{c.retry}</button>}
      {((history.store.retained_projects ?? history.store.projects.length) > 0 || history.error) && <button type="button" disabled={pending || busy} onClick={() => void clear(true)}>{c.clearAll}</button>}
    </div>
    {open && changes && observation && saved && <div id={`${id}-changes`} className="resume-comparison-results">
      <p>{c.current} · {c.observed}: <time dateTime={observation.inspectedAt}>{formatAbsolute(observation.inspectedAt, locale)}</time></p>
      <p>{c.limits}</p>
      {(saved.baseline.sourcesOmitted || observation.sourcesOmitted) && <p>{c.omitted}</p>}
      <h3>{c.metadata}</h3>
      <ul>{changes.filter((row) => row.kind === 'field').map((row) => <ChangeRow key={row.name} row={row} copy={c} onOpenSource={onOpenSource} />)}</ul>
      <h3>{c.sources}</h3>
      <ul>{changes.filter((row) => row.kind === 'source').map((row) => <ChangeRow key={row.name} row={row} copy={c} onOpenSource={onOpenSource} />)}</ul>
    </div>}
  </section>;
}
