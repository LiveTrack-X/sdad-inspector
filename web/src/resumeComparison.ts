import { doctorResult } from './doctorResult';
import type { Snapshot } from './types';

export const MAX_RESUME_PROJECTS = 8;
export const MAX_RESUME_BYTES = 192 * 1024;
const MAX_SOURCES = 32;
const MAX_TEXT = 1024;
const MAX_PATH = 1024;
export const RESUME_FIELDS = ['packet', 'objective', 'status', 'gates', 'spec', 'handoff'] as const;
export type ResumeField = typeof RESUME_FIELDS[number];
export type ComparisonStatus = 'unchanged' | 'changed' | 'unknown';
export interface RecordedValue { text: string | null; complete: boolean }
export interface SourceIdentity { path: string; exists: boolean | null; sha256: string | null }
export interface ResumeObservation {
  projectIdentity: string;
  projectRoot: string;
  inspectionId: string;
  inspectedAt: string;
  statePath: string;
  fields: Record<ResumeField, RecordedValue>;
  sources: SourceIdentity[];
  sourcesOmitted: boolean;
}
export interface ResumeProject {
  baseline: ResumeObservation;
  latest: ResumeObservation;
}
export interface ResumeStore { version: 1; projects: ResumeProject[]; retained_projects?: number }
export interface ResumeChange {
  kind: 'field' | 'source';
  name: string;
  before: string | null;
  after: string | null;
  status: ComparisonStatus;
  sourcePath: string;
}

function bounded(value: string | null): RecordedValue {
  const characters = value === null ? [] : Array.from(value);
  return { text: value === null ? null : characters.slice(0, MAX_TEXT).join(''), complete: characters.length <= MAX_TEXT };
}
function sha(value: unknown): string | null {
  return typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value) ? value.toLowerCase() : null;
}
function validText(value: unknown, max = MAX_TEXT): value is string {
  return typeof value === 'string' && value.length > 0 && Array.from(value).length <= max;
}
function validTime(value: unknown): value is string {
  return validText(value, 64) && /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value));
}

/** One observation uses one completed snapshot only, never later live-document reads. */
export function resumeObservation(snapshot: Snapshot): ResumeObservation | null {
  if (!snapshot.state.available || !doctorResult(snapshot).available
    || !validText(snapshot.project.identity) || !validText(snapshot.project.root, 2048)
    || !validText(snapshot.inspection_id) || !validTime(snapshot.inspected_at)
    || !validText(snapshot.protocol.state_path, MAX_PATH)) return null;
  const packet = snapshot.state.active_packet;
  const gates = snapshot.state.owner_gates;
  const gateValue = bounded(gates.join('\n'));
  const handoff = snapshot.state.current_handoff;
  const paths = [...new Set([
    snapshot.protocol.state_path, snapshot.state.active_spec?.path,
    snapshot.protocol.todo_path, snapshot.protocol.findings_path,
    handoff?.declared ? handoff.path : null,
    ...Object.keys(snapshot.evidence.files),
  ].filter((path): path is string => Boolean(path)))].sort();
  const eligiblePaths = paths.filter((path) => validText(path, MAX_PATH));
  return {
    projectIdentity: snapshot.project.identity, projectRoot: snapshot.project.root,
    inspectionId: snapshot.inspection_id, inspectedAt: snapshot.inspected_at,
    statePath: snapshot.protocol.state_path,
    fields: {
      packet: bounded(packet?.id ?? null), objective: bounded(packet?.objective ?? null),
      status: bounded(packet?.status ?? null), gates: gateValue,
      spec: bounded(snapshot.state.active_spec?.path ?? null),
      handoff: bounded(handoff?.declared ? handoff.path : null),
    },
    sources: eligiblePaths.slice(0, MAX_SOURCES).map((path) => {
      const metadata = snapshot.evidence.files[path];
      const exists = typeof metadata?.exists === 'boolean' ? metadata.exists : null;
      return { path, exists, sha256: exists === true ? sha(metadata?.sha256) : null };
    }),
    sourcesOmitted: eligiblePaths.length !== paths.length || eligiblePaths.length > MAX_SOURCES,
  };
}

export function sameResumeProject(a: Pick<ResumeObservation, 'projectIdentity' | 'projectRoot'>, b: Pick<ResumeObservation, 'projectIdentity' | 'projectRoot'>): boolean {
  return a.projectIdentity === b.projectIdentity && a.projectRoot === b.projectRoot;
}
export function resumeProject(store: ResumeStore, project: Pick<ResumeObservation, 'projectIdentity' | 'projectRoot'>): ResumeProject | undefined {
  return store.projects.find((entry) => sameResumeProject(entry.baseline, project));
}

export function compareResumeObservations(before: ResumeObservation, after: ResumeObservation): ResumeChange[] | null {
  if (!sameResumeProject(before, after)) return null;
  const fields: ResumeChange[] = RESUME_FIELDS.map((name) => ({
    kind: 'field', name, before: before.fields[name].text, after: after.fields[name].text,
    status: !before.fields[name].complete || !after.fields[name].complete ? 'unknown'
      : before.fields[name].text === after.fields[name].text ? 'unchanged' : 'changed',
    sourcePath: after.statePath,
  }));
  const sources: ResumeChange[] = [...new Set([...before.sources, ...after.sources].map((source) => source.path))].sort().map((path) => {
    const old = before.sources.find((source) => source.path === path);
    const next = after.sources.find((source) => source.path === path);
    const status: ComparisonStatus = !old || !next || old.exists === null || next.exists === null ? 'unknown'
      : old.exists !== next.exists ? 'changed'
        : old.exists === false ? 'unchanged'
          : !old.sha256 || !next.sha256 ? 'unknown'
            : old.sha256 === next.sha256 ? 'unchanged' : 'changed';
    return { kind: 'source', name: path, before: old?.exists === false ? 'absent' : old?.sha256 ?? null,
      after: next?.exists === false ? 'absent' : next?.sha256 ?? null, status, sourcePath: path };
  });
  return [...fields, ...sources];
}
