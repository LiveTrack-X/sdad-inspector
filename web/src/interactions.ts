export interface InteractionRecord {
  version: 1; id: string; kind: 'request' | 'interpretation' | 'progress' | 'decision' | 'response';
  packet: string; request_id: string; base_revision: string; author: string; reported_at: string;
  summary: string; source_ref?: string; scope?: string[]; excluded?: string[]; assumptions?: string[];
  remaining?: string[]; impact?: string[]; alternatives?: string[]; reason?: string; owner_question?: string;
  result_revision?: string; supersedes?: string; correction_id?: string; stage?: string;
  criteria?: Array<{ id: string; summary: string; status: string }>;
  evidence?: Array<{ path: string; result: string }>;
  source: { path: string; line: number; sha256: string };
  link_status: 'matched' | 'stale' | 'conflict' | 'other_packet' | 'unresolved' | 'superseded';
}
export interface InteractionProjection {
  schema_version: number; project_root: string; packet: string | null; observed_at: string;
  status: string; records: InteractionRecord[]; issues: Array<{code: string; path: string; line: number}>;
}
export interface Correction {
  id: string; request_id: string; packet: string; base_revision: string; project_root: string;
  before: string; correction: string; supersedes: string; copy_state: 'draft' | 'sealed' | 'copied';
  revision?: number;
}
export function correctionParent(rows: Correction[], selected: Correction | null): string {
  if (selected && rows.some(r => r.id === selected.id)) return selected.id;
  const replaced = new Set(rows.map(r => r.supersedes));
  const leaves = rows.filter(r => !replaced.has(r.id));
  return leaves.length === 1 ? leaves[0].id : '';
}
export function responseState(draft: Correction, records: InteractionRecord[], incomplete: boolean, currentRevision = draft.base_revision): string {
  if (incomplete) return 'unconfirmed';
  const responses = records.filter(r => r.kind === 'response' && r.correction_id === draft.id && r.packet === draft.packet && r.request_id === draft.request_id && r.base_revision === draft.base_revision);
  if (currentRevision !== draft.base_revision && !responses.some(r => r.link_status === 'matched' && r.result_revision === currentRevision)) return 'stale';
  if (responses.some(r => r.link_status === 'conflict')) return 'conflict';
  const stages = ['verification_reported', 'applied', 'planned', 'acknowledged'];
  return stages.find(stage => responses.some(r => r.link_status === 'matched' && r.stage === stage)) ?? draft.copy_state;
}
export function correctionText(d: Correction): string {
  return `SDAD correction request (v1)\nProject: ${d.project_root}\nPacket: ${d.packet}\nRequest: ${d.request_id}\nCorrection ID: ${d.id}\nBase revision: ${d.base_revision}\nSupersedes correction: ${d.supersedes || '(none)'}\n\nPrevious interpretation:\n${d.before}\n\nRequested correction:\n${d.correction}\n\nImpact: awaiting AI report.\nPlease acknowledge this exact correction ID, request, packet and base revision; report the understood change, affected scope, plan, remaining work, and actual validation results with evidence; when the requirement revision changes, include result_revision in applied or verification_reported responses in the existing routed Markdown authorities using sdad-interaction v1 response records. Do not treat copying this draft as delivery, approval, acceptance, or evidence of execution.`;
}
