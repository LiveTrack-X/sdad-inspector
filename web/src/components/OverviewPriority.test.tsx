import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { resumeComparisonAction } from '../api';
import { I18nProvider } from '../i18n';
import { packetWorkItems } from '../packetWork';
import { resumeObservation, type ResumeProject } from '../resumeComparison';
import { selectionFor } from '../selection';
import { activityFixture, liveDocumentsFixture, snapshotFixture } from '../test/fixture';
import type { DevelopmentActivity } from '../types';
import { DevelopmentFlowView, PacketHistoryPanel } from './DevelopmentFlow';
import { Overview } from './Overview';
import { ResumeComparison } from './ResumeComparison';

vi.mock('./InteractionPanel', () => ({ InteractionPanel: () => <section aria-label="Request interpretation"><h2>Request interpretation</h2><button>Correct the interpretation</button></section> }));
vi.mock('./VerificationRecords', () => ({ VerificationRecords: () => <section aria-label="Verification records"><h2>Verification records</h2><button>Read verification records</button></section> }));
vi.mock('../api', async (importOriginal) => ({ ...await importOriginal<typeof import('../api')>(), resumeComparisonAction: vi.fn() }));
const action = vi.mocked(resumeComparisonAction);
const todo = liveDocumentsFixture.documents.find((document) => document.path === snapshotFixture.protocol.todo_path)!;
const work = packetWorkItems(todo.content, snapshotFixture.state.active_packet!.id);

beforeEach(() => {
  let saved: ResumeProject | null = null;
  action.mockReset();
  action.mockImplementation(async (_root, _id, mode) => {
    if (mode === 'enable') saved = { baseline: resumeObservation(snapshotFixture)!, latest: resumeObservation(snapshotFixture)! };
    return { version: 1, projects: saved ? [saved] : [], retained_projects: saved ? 1 : 0 };
  });
});

function before(first: Element, next: Element) {
  expect(first.compareDocumentPosition(next) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
}
function overview(selectedId = 'overview', onSelect = vi.fn()) {
  return <I18nProvider><Overview snapshot={snapshotFixture} selectedId={selectedId}
    selection={selectionFor(snapshotFixture, selectedId, ((key: string) => key) as Parameters<typeof selectionFor>[2], work, true)}
    busy={false} progress={null} liveDocuments={liveDocumentsFixture} activity={activityFixture}
    packetWork={work} rule5={null} onSelect={onSelect}
    continuity={<ResumeComparison snapshot={snapshotFixture} onOpenSource={onSelect}/>}/></I18nProvider>;
}

describe('overview priorities', () => {
  it('places packet interpretation and current work before resume, verification and collapsed history', async () => {
    const onSelect = vi.fn();
    const { container } = render(overview('overview', onSelect));
    await waitFor(() => expect(action).toHaveBeenCalledTimes(1));
    const packet = screen.getByRole('heading', { name: snapshotFixture.state.active_packet!.id });
    const interpretation = screen.getByRole('heading', { name: 'Request interpretation' });
    const current = screen.getByRole('heading', { name: 'Current packet TODO' });
    const resume = screen.getByRole('heading', { name: 'Resume comparison' });
    const verification = screen.getByRole('heading', { name: 'Verification records' });
    const doctor = screen.getByRole('heading', { name: 'Doctor Summary' });
    const history = container.querySelector('details.repository-history')!;
    before(packet, interpretation); before(interpretation, current);
    before(current, resume); before(resume, verification); before(verification, doctor); before(doctor, history);
    expect(history).not.toHaveAttribute('open');
    expect(screen.getByText('Build the browser MVP')).not.toBeVisible();
    expect(screen.getByRole('button', { name: 'Correct the interpretation' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Read verification records' })).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Open remaining work in the full TODO' }));
    expect(onSelect).toHaveBeenCalledWith('todo');
    fireEvent.click(history.querySelector('summary')!);
    expect(history).toHaveAttribute('open');
    expect(screen.getByText('Build the browser MVP')).toBeVisible();
    expect(screen.getByText('Progress handoff')).toBeVisible();
    expect(screen.getByText('web/src/App.tsx')).toBeVisible();
  });

  it('keeps the same resume instance and expanded comparison across navigation without observing twice', async () => {
    const mounted = render(overview());
    const enable = screen.getByRole('button', { name: 'Enable and save baseline' });
    await waitFor(() => expect(enable).toBeEnabled());
    fireEvent.click(enable);
    const compare = await screen.findByRole('button', { name: 'Compare with saved baseline' });
    await waitFor(() => expect(compare).toBeEnabled());
    fireEvent.click(compare);
    const original = mounted.container.querySelector('.resume-comparison');
    const calls = action.mock.calls.length;
    mounted.rerender(overview('state'));
    expect(mounted.container.querySelectorAll('.resume-comparison')).toHaveLength(1);
    expect(original).not.toBeVisible();
    expect(screen.getByRole('heading', { name: 'Repository state' })).toBeVisible();
    mounted.rerender(overview());
    expect(mounted.container.querySelector('.resume-comparison')).toBe(original);
    expect(screen.getByRole('button', { name: 'Close comparison' })).toBeVisible();
    expect(action.mock.calls).toHaveLength(calls);
  });

  it('keeps Development Flow work and verification above the history disclosure and preserves its filters', () => {
    const { container } = render(<I18nProvider><DevelopmentFlowView snapshot={snapshotFixture} documents={liveDocumentsFixture} activity={activityFixture} work={work} onSelect={vi.fn()}/></I18nProvider>);
    const history = container.querySelector('details.repository-history')!;
    before(screen.getByRole('heading', { name: 'Current packet TODO' }), screen.getByRole('heading', { name: 'Verification records' }));
    before(screen.getByRole('heading', { name: 'Verification records' }), history);
    expect(history).not.toHaveAttribute('open');
    fireEvent.click(history.querySelector('summary')!);
    expect(screen.getByRole('button', { name: 'Filter changed files to the Implementation lens (1 paths)' })).toBeEnabled();
  });
});

describe('history disclosure evidence and locales', () => {
  it.each(['missing', 'wrong-project', 'unavailable', 'truncated'] as const)('retains unknown totals for %s observations', (kind) => {
    const activity: DevelopmentActivity | null = kind === 'missing' ? null : {
      ...activityFixture,
      ...(kind === 'wrong-project' ? { project_root: 'C:\\other' } : {}),
      ...(kind === 'unavailable' ? { available: false, files: [], commits: [], error: { code: 'failed', message: 'Unavailable' } } : {}),
      ...(kind === 'truncated' ? { truncated: true } : {}),
    };
    const { container } = render(<I18nProvider><PacketHistoryPanel snapshot={snapshotFixture} activity={activity}/></I18nProvider>);
    const summary = container.querySelector('summary')!;
    expect(within(summary).getAllByText('unavailable').length).toBeGreaterThan(0);
    fireEvent.click(summary);
    if (kind === 'truncated') {
      expect(screen.getByText('The changed-file list is partial; its total is unavailable.')).toBeVisible();
      expect(screen.getByText('web/src/App.tsx')).toBeVisible();
    } else {
      expect(screen.getByText(/Repository observations are unavailable/)).toBeVisible();
      if (kind === 'wrong-project') expect(screen.queryByText('web/src/App.tsx')).not.toBeInTheDocument();
    }
  });

  it.each([
    ['en', 'Git and handoff history'],
    ['ko', 'Git·핸드오프 이력'],
    ['ja', 'Git・ハンドオフ履歴'],
    ['zh-CN', 'Git 与交接历史'],
  ])('keeps a visible native disclosure and counts in %s', (locale, label) => {
    Object.defineProperty(navigator, 'languages', { configurable: true, value: [locale] });
    const { container } = render(<I18nProvider><PacketHistoryPanel snapshot={snapshotFixture} activity={activityFixture}/></I18nProvider>);
    const title = screen.getByText(label, { selector: 'summary > strong' });
    expect(title).toBeVisible();
    expect(container.querySelector('details')).not.toHaveAttribute('open');
    expect(within(title.parentElement!).getByText('2')).toBeVisible();
    expect(within(title.parentElement!).getAllByText('1')).toHaveLength(2);
  });
});
