import { describe, expect, it } from 'vitest';
import { snapshotFixture } from './test/fixture';
import { compareResumeObservations, resumeObservation, resumeProject } from './resumeComparison';

export function comparisonSnapshot(index = 0) {
  const snapshot = structuredClone(snapshotFixture);
  snapshot.inspection_id = `observation-${index}`;
  snapshot.inspected_at = new Date(Date.UTC(2026, 8, 20, 10, index)).toISOString();
  for (const path of [snapshot.protocol.state_path, snapshot.protocol.todo_path, snapshot.protocol.findings_path, snapshot.state.active_spec!.path]) {
    snapshot.evidence.files[path] = { exists: true, sha256: 'a'.repeat(64) };
  }
  return snapshot;
}
function observation(index = 0) { return resumeObservation(comparisonSnapshot(index))!; }


describe('coherent resume observations', () => {
  it('stores bounded state metadata and snapshot source identities, never document bodies or commands', () => {
    const snapshot = comparisonSnapshot();
    snapshot.evidence.files[snapshot.protocol.todo_path].content = 'PRIVATE DOCUMENT BODY';
    snapshot.evidence.doctor_report.secret = 'UNRELATED REPORT BODY';
    const saved = resumeObservation(snapshot)!;
    expect(saved.sources.find((source) => source.path === snapshot.protocol.todo_path)?.sha256).toBe('a'.repeat(64));
    expect(saved.inspectedAt).toBe(snapshot.inspected_at);
    expect(JSON.stringify(saved)).not.toMatch(/PRIVATE DOCUMENT|UNRELATED REPORT|npm test|doctor_report/);
    expect(saved.fields.objective.text).toBe(snapshot.state.active_packet!.objective);
  });

  it.each(['stale', 'diagnostic', 'failed'])('rejects %s scans instead of replacing successful observations', (status) => {
    const snapshot = comparisonSnapshot();
    snapshot.inspection_status = status;
    expect(resumeObservation(snapshot)).toBeNull();
  });

  it('rejects missing state, unfinished Doctor, unstable controls and invalid observation times', () => {
    for (const mutate of [
      (s: ReturnType<typeof comparisonSnapshot>) => { s.state.available = false; },
      (s: ReturnType<typeof comparisonSnapshot>) => { s.doctor.completed = false; },
      (s: ReturnType<typeof comparisonSnapshot>) => { s.integrity.control_files_unchanged_during_inspection = false; },
      (s: ReturnType<typeof comparisonSnapshot>) => { s.inspected_at = 'not a timestamp'; },
    ]) {
      const snapshot = comparisonSnapshot(); mutate(snapshot);
      expect(resumeObservation(snapshot)).toBeNull();
    }
  });

  it('allows an observed structural finding without interpreting it as passed verification', () => {
    const snapshot = comparisonSnapshot();
    snapshot.doctor.exit_code = 1; snapshot.doctor.summary.errors = 1;
    const record = resumeObservation(snapshot)!;
    expect(record).not.toBeNull();
    expect(record).not.toHaveProperty('verified');
    expect(record.fields.status.text).toBe('software_verified'); // The declaration remains verbatim.
  });

  it('compares changed objective, gate, checkpoint and source hash while preserving unknown hashes', () => {
    const before = observation();
    const snapshot = comparisonSnapshot(1);
    snapshot.state.active_packet!.objective = 'A corrected objective';
    snapshot.state.owner_gates = ['local work only'];
    snapshot.state.current_handoff = { path: 'docs/checkpoint.md', declared: true, exists: true };
    snapshot.evidence.files[snapshot.protocol.todo_path].sha256 = 'b'.repeat(64);
    delete snapshot.evidence.files[snapshot.state.active_spec!.path].sha256;
    const rows = compareResumeObservations(before, resumeObservation(snapshot)!)!;
    expect(rows.find((row) => row.name === 'objective')?.status).toBe('changed');
    expect(rows.find((row) => row.name === 'gates')?.status).toBe('changed');
    expect(rows.find((row) => row.name === 'handoff')?.status).toBe('changed');
    expect(rows.find((row) => row.name === snapshot.protocol.todo_path)?.status).toBe('changed');
    expect(rows.find((row) => row.name === snapshot.state.active_spec!.path)?.status).toBe('unknown');
    expect(rows.find((row) => row.name === 'status')?.status).toBe('unchanged');
  });

  it('does not call equal clipped text unchanged or equate missing hashes', () => {
    const snapshot = comparisonSnapshot();
    snapshot.state.active_packet!.objective = 'x'.repeat(1100);
    snapshot.state.owner_gates = Array.from({ length: 13 }, (_, i) => `gate ${i}: ${'x'.repeat(100)}`);
    snapshot.evidence.files[snapshot.protocol.todo_path] = { exists: true };
    const before = resumeObservation(snapshot)!;
    snapshot.state.active_packet!.objective += 'different hidden ending';
    const rows = compareResumeObservations(before, resumeObservation(snapshot)!)!;
    expect(rows.find((row) => row.name === 'objective')?.status).toBe('unknown');
    expect(rows.find((row) => row.name === 'gates')?.status).toBe('unknown');
    expect(rows.find((row) => row.name === snapshot.protocol.todo_path)?.status).toBe('unknown');
  });

  it('bounds Unicode metadata by code point, consistently with the server observation', () => {
    const snapshot = comparisonSnapshot();
    snapshot.state.active_packet!.objective = '😀'.repeat(1025);
    const record = resumeObservation(snapshot)!;
    expect(record.fields.objective.text).toBe('😀'.repeat(1024));
    expect(record.fields.objective.complete).toBe(false);
  });

  it('compares absence separately and never infers that a source removed from observation was deleted', () => {
    const before = observation();
    const after = observation(1);
    after.sources[0].exists = false; after.sources[0].sha256 = null;
    const removedPath = after.sources.pop()!.path;
    const rows = compareResumeObservations(before, after)!;
    expect(rows.find((row) => row.name === after.sources[0].path)?.status).toBe('changed');
    expect(rows.find((row) => row.name === removedPath)?.status).toBe('unknown');
    expect(compareResumeObservations(after, after)?.find((row) => row.name === after.sources[0].path)?.status).toBe('unchanged');
  });

  it.each(['projectIdentity', 'projectRoot'] as const)('isolates projects by %s as well as the other identity field', (field) => {
    const before = observation();
    const after = { ...observation(1), [field]: 'another project' };
    expect(compareResumeObservations(before, after)).toBeNull();
    const store = { version: 1 as const, projects: [{ baseline: before, latest: before }] };
    expect(resumeProject(store, after)).toBeUndefined();
  });
});
