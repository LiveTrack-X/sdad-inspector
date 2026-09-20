import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { resumeComparisonAction } from '../api';
import { I18nProvider } from '../i18n';
import { resumeObservation, type ResumeProject } from '../resumeComparison';
import { snapshotFixture } from '../test/fixture';
import type { Snapshot } from '../types';
import { ResumeComparison } from './ResumeComparison';

vi.mock('../api', () => ({ resumeComparisonAction: vi.fn() }));
const action = vi.mocked(resumeComparisonAction);
let entries: Map<string, ResumeProject>;
let serverSnapshots: Map<string, Snapshot>;
function snapshot(index = 0): Snapshot {
  const next = structuredClone(snapshotFixture);
  next.inspection_id = `scan-${index}`;
  next.inspected_at = new Date(Date.UTC(2026, 8, 20, 10, index)).toISOString();
  next.evidence.files[next.protocol.state_path] = { exists: true, sha256: 'a'.repeat(64) };
  next.evidence.files[next.protocol.todo_path] = { exists: true, sha256: 'a'.repeat(64) };
  return next;
}
function view(current: Snapshot, onOpenSource = vi.fn()) {
  serverSnapshots.set(current.project.root, current);
  return <StrictMode><I18nProvider><ResumeComparison snapshot={current} onOpenSource={onOpenSource} /></I18nProvider></StrictMode>;
}
async function enable() {
  const button = await screen.findByRole('button', { name: 'Enable and save baseline' });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Compare with saved baseline' })).toBeEnabled());
}
function row(name: string) {
  return screen.getAllByText(name, { selector: '.resume-change-heading strong' })[0].closest('li')!;
}
function deferredStore() {
  let resolve!: (store: Awaited<ReturnType<typeof resumeComparisonAction>>) => void;
  const promise = new Promise<Awaited<ReturnType<typeof resumeComparisonAction>>>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en'] });
  entries = new Map(); serverSnapshots = new Map(); action.mockReset();
  action.mockImplementation(async (root, id, operation) => {
    const current = serverSnapshots.get(root)!;
    if (!current || current.inspection_id !== id) throw new Error('stale request');
    const candidate = resumeObservation(current);
    const existing = entries.get(root);
    if (operation === 'clear_all') entries.clear();
    else if (operation === 'clear') entries.delete(root);
    else if ((operation === 'enable' || operation === 'replace' || operation === 'observe' && existing) && candidate) {
      entries.set(root, { baseline: !existing || operation === 'replace' ? candidate : existing.baseline, latest: candidate });
    }
    return { version: 1, projects: entries.has(root) ? [entries.get(root)!] : [], retained_projects: entries.size };
  });
});

describe('resume comparison controls', () => {
  it('requires explicit opt-in and does not send document text or persist browser-origin history', async () => {
    const current = snapshot();
    render(view(current));
    await waitFor(() => expect(action).toHaveBeenCalled());
    expect(entries.size).toBe(0);
    expect(action.mock.calls.every(([, , mode]) => mode === 'observe')).toBe(true);
    expect(screen.getByText(/Document bodies are not stored/)).toBeVisible();
    expect(await screen.findByText('No saved comparison baseline')).toBeVisible();
    expect(screen.getByText(/changes made before now cannot be reconstructed/)).toBeVisible();
    expect(screen.getByText(/starting point to compare future changes/)).toBeVisible();
    expect(screen.getByText(/The inspected project stays read-only/)).toBeVisible();
    await enable();
    expect(screen.queryByText('No saved comparison baseline')).not.toBeInTheDocument();
    expect(action).toHaveBeenCalledWith(current.project.root, current.inspection_id, 'enable');
    expect(action.mock.calls.every((call) => call.length === 3)).toBe(true);
    expect(Object.keys(localStorage).some((key) => key.includes('resume'))).toBe(false);
    expect(screen.queryByRole('heading', { name: 'Declared state' })).not.toBeInTheDocument();
  });

  it('confirms absence only after loading finishes and never enables saving while history is unknown', async () => {
    const response = deferredStore();
    action.mockReturnValue(response.promise);
    render(view(snapshot()));
    expect(screen.getByText('Checking saved comparison history…')).toBeVisible();
    expect(screen.queryByText('No saved comparison baseline')).not.toBeInTheDocument();
    expect(screen.queryByText(/changes made before now cannot be reconstructed/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeDisabled();
    await act(async () => response.resolve({ version: 1, projects: [], retained_projects: 0 }));
    expect(screen.getByText('No saved comparison baseline')).toBeVisible();
    expect(screen.queryByText('Checking saved comparison history…')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeEnabled();
    expect(action.mock.calls.every(([, , mode]) => mode === 'observe')).toBe(true);
    expect(entries.size).toBe(0);
  });

  it('does not carry confirmed absence across scans or projects, including a late previous-project read', async () => {
    const before = snapshot();
    const mounted = render(view(before));
    await screen.findByText('No saved comparison baseline');
    const oldResponse = deferredStore();
    const currentResponse = deferredStore();
    action.mockImplementation((root) => root === before.project.root ? oldResponse.promise : currentResponse.promise);
    mounted.rerender(view(snapshot(1)));
    expect(screen.queryByText('No saved comparison baseline')).not.toBeInTheDocument();
    expect(screen.getByText('Checking saved comparison history…')).toBeVisible();
    const other = snapshot(2); other.project = { ...other.project, root: 'C:\\other', identity: 'other' };
    mounted.rerender(view(other));
    await act(async () => oldResponse.resolve({ version: 1, projects: [], retained_projects: 0 }));
    expect(screen.queryByText('No saved comparison baseline')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeDisabled();
    await act(async () => currentResponse.resolve({ version: 1, projects: [], retained_projects: 0 }));
    expect(screen.getByText('No saved comparison baseline')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeEnabled();
    expect(entries.size).toBe(0);
  });

  it('keeps an unavailable current inspection distinct from confirmed missing history', async () => {
    const stale = snapshot(); stale.inspection_status = 'stale';
    render(view(stale));
    await screen.findByText('No saved comparison baseline');
    expect(screen.getByText(/A coherent completed inspection with readable state is required/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeDisabled();
    expect(action.mock.calls.every(([, , mode]) => mode === 'read')).toBe(true);
    expect(entries.size).toBe(0);
  });

  it('retains the pinned baseline across StrictMode, new scans and a page remount, then compares explicitly', async () => {
    const before = snapshot();
    const mounted = render(view(before));
    await enable();
    mounted.unmount();
    const after = snapshot(1);
    after.state.active_packet!.objective = 'A revised objective';
    after.state.active_packet!.status = 'deferred';
    after.evidence.files[after.protocol.todo_path].sha256 = 'b'.repeat(64);
    const openSource = vi.fn();
    render(view(after, openSource));
    const compare = await screen.findByRole('button', { name: 'Compare with saved baseline' });
    await waitFor(() => expect(compare).toBeEnabled());
    expect(entries.get(before.project.root)!.baseline.inspectionId).toBe(before.inspection_id);
    expect(entries.get(before.project.root)!.latest.inspectionId).toBe(after.inspection_id);
    fireEvent.click(compare);
    expect(within(row('Objective')).getByText(before.state.active_packet!.objective)).toBeVisible();
    expect(within(row('Objective')).getByText('A revised objective')).toBeVisible();
    expect(within(row('Declared status')).getByText('deferred')).toBeVisible();
    expect(within(row(after.protocol.todo_path)).getByText('Changed')).toBeVisible();
    expect(screen.getByText(/cannot authorize work, reactivate a deferred packet/)).toBeVisible();
    fireEvent.click(within(row('Objective')).getByRole('button', { name: /Open current source/ }));
    expect(openSource).toHaveBeenCalledWith(after.protocol.state_path);
  });

  it('does not replace the baseline or latest observation with stale or diagnostic scans', async () => {
    const before = snapshot();
    const mounted = render(view(before));
    await enable();
    for (const status of ['stale', 'diagnostic']) {
      const after = snapshot(1); after.inspection_status = status;
      mounted.rerender(view(after));
      await waitFor(() => expect(action).toHaveBeenLastCalledWith(after.project.root, after.inspection_id, 'read'));
      expect(screen.getByRole('button', { name: 'Use current observation as baseline' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Compare with saved baseline' })).toBeDisabled();
      expect(entries.get(before.project.root)!.latest.inspectionId).toBe(before.inspection_id);
    }
  });

  it('replaces only on explicit action, then clear disables retention without deleting another project', async () => {
    const before = snapshot();
    const other = snapshot(); other.project = { ...other.project, root: 'C:\\other', identity: 'other' };
    const otherRecord = resumeObservation(other)!;
    entries.set(other.project.root, { baseline: otherRecord, latest: otherRecord });
    const mounted = render(view(before)); await enable();
    const after = snapshot(1); after.state.active_packet!.objective = 'Changed';
    mounted.rerender(view(after));
    const replace = screen.getByRole('button', { name: 'Use current observation as baseline' });
    await waitFor(() => expect(replace).toBeEnabled());
    fireEvent.click(replace);
    await waitFor(() => expect(entries.get(after.project.root)!.baseline.inspectionId).toBe(after.inspection_id));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Clear this project and disable' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Clear this project and disable' }));
    await screen.findByRole('button', { name: 'Enable and save baseline' });
    expect(entries.has(other.project.root)).toBe(true);
    mounted.rerender(view(snapshot(2)));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeEnabled());
    expect(entries.has(before.project.root)).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Clear all comparison history' }));
    await waitFor(() => expect(entries.size).toBe(0));
  });

  it('keeps projects separate and rejects a late previous-project response', async () => {
    const before = snapshot();
    const mounted = render(view(before)); await enable();
    const oldEntry = entries.get(before.project.root)!;
    const other = snapshot(1); other.project = { ...other.project, root: 'C:\\other', identity: 'other' };
    action.mockResolvedValueOnce({ version: 1, projects: [oldEntry], retained_projects: 1 });
    mounted.rerender(view(other));
    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: 'Compare with saved baseline' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeDisabled();
  });

  it('shows unknown source identity instead of treating absence of hashes as a match', async () => {
    render(view(snapshot())); await enable();
    fireEvent.click(screen.getByRole('button', { name: 'Compare with saved baseline' }));
    expect(within(row(snapshotFixture.state.active_spec!.path)).getByText('Unknown')).toBeVisible();
    expect(within(row(snapshotFixture.protocol.todo_path)).getByText('Unchanged')).toBeVisible();
  });

  it('requires a rescan when another window has retained a newer observation', async () => {
    const baseline = resumeObservation(snapshot())!;
    const latest = resumeObservation(snapshot(2))!;
    action.mockResolvedValue({ version: 1, projects: [{ baseline, latest }], retained_projects: 1 });
    render(view(snapshot(1)));
    await screen.findByText(/A newer observation was saved by another view/);
    expect(screen.getByRole('button', { name: 'Compare with saved baseline' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Use current observation as baseline' })).toBeDisabled();
  });

  it('handles failed history loading with an explicit retry and no implied opt-in', async () => {
    action.mockRejectedValueOnce(new Error('offline')).mockRejectedValueOnce(new Error('offline'));
    render(view(snapshot()));
    await screen.findByRole('alert');
    expect(screen.queryByText('No saved comparison baseline')).not.toBeInTheDocument();
    expect(screen.queryByText(/changes made before now cannot be reconstructed/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enable and save baseline' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Retry reading history' }));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByText('No saved comparison baseline')).toBeVisible();
    expect(entries.size).toBe(0);
  });

  it.each([
    ['ko', '재개 전 변경 비교', '켜고 비교 기준 저장', '저장된 비교 기준 없음'],
    ['ja', '再開前の変更比較', '有効にして比較基準を保存', '保存した比較基準がありません'],
    ['zh-CN', '恢复前变更比较', '启用并保存比较基准', '尚未保存比较基准'],
  ])('localizes comparison controls and confirmed absence in %s', async (locale, title, enableLabel, emptyLabel) => {
    Object.defineProperty(navigator, 'languages', { configurable: true, value: [locale] });
    render(view(snapshot()));
    expect(screen.getByRole('heading', { name: title })).toBeVisible();
    await waitFor(() => expect(screen.getByRole('button', { name: enableLabel })).toBeEnabled());
    expect(screen.getByText(emptyLabel)).toBeVisible();
  });
});
