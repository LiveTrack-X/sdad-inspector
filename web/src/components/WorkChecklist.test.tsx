import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n';
import { packetWorkItems } from '../packetWork';
import { liveDocumentsFixture, snapshotFixture } from '../test/fixture';
import { workChecklistCopy } from '../workChecklistCopy';
import { PacketWorkPanel } from './DevelopmentFlow';

const packet = snapshotFixture.state.active_packet!.id;
const markdown = `## Active Work
- [ ] [packet:${packet}] [current] [phase:Implement] Show current work.
- [ ] [packet:${packet}] [phase:Verify] Check the visible behavior.
- [x] [packet:${packet}] [current] [phase:Plan] Record the scope.
## Future / Deferred
### Waiting for a decision
- [ ] [packet:${packet}] [current] [phase:Implement] Keep the deferred experiment.
- [ ] [packet:another-packet] Do not resume another packet.`;

function show(kind = 'normal', locale = 'en') {
  Object.defineProperty(navigator, 'languages', { configurable: true, value: [locale] });
  const snapshot = kind.startsWith('deferred') ? { ...snapshotFixture, state: { ...snapshotFixture.state,
    active_packet: { ...snapshotFixture.state.active_packet!, status: 'deferred' } } } : snapshotFixture;
  const documents = { ...liveDocumentsFixture, documents: liveDocumentsFixture.documents.map(doc =>
    doc.path === snapshot.protocol.todo_path ? { ...doc, content: markdown, truncated: kind.endsWith('truncated') } : doc) };
  return render(<I18nProvider><PacketWorkPanel snapshot={snapshot} documents={documents}
    work={packetWorkItems(markdown, packet)} onSelect={vi.fn()}/></I18nProvider>);
}

describe('separate current, remaining, checked and deferred work', () => {
  it('keeps authored tasks intact and excludes deferred and checked markers from current work', () => {
    const { container } = show();
    expect(container.querySelector('.current-todo-callout')).toHaveTextContent('Show current work.');
    expect(container.querySelector('.current-todo-callout')).not.toHaveTextContent('Record the scope.');
    expect(container.querySelector('.current-todo-callout')).not.toHaveTextContent('Keep the deferred experiment.');
    const remaining = screen.getByRole('group', { name: 'Other open tasks' });
    expect(remaining).toHaveTextContent('Check the visible behavior.');
    expect(remaining).not.toHaveTextContent('Keep the deferred experiment.');
    expect(remaining).toHaveTextContent('Shown in source order.');
    expect(screen.getByRole('group', { name: 'Checked tasks' })).toHaveTextContent('Record the scope.');
    expect(screen.getByRole('group', { name: 'Deferred tasks' })).toHaveTextContent('Keep the deferred experiment.');
    expect(screen.queryByText('Do not resume another packet.')).not.toBeInTheDocument();
  });

  it('keeps every open task in the deferred group when the packet is deferred', () => {
    show('deferred');
    const deferred = screen.getByRole('group', { name: 'Deferred tasks' });
    expect(deferred).toHaveTextContent('Show current work.');
    expect(deferred).toHaveTextContent('Check the visible behavior.');
    expect(screen.getByRole('group', { name: 'Other open tasks' })).not.toHaveTextContent('Check the visible behavior.');
    const summary = within(deferred).getByText('Show current work.', { selector: 'summary span' });
    fireEvent.click(summary);
    expect(within(summary.closest('details')!).getByText('Recorded [current] marker; active work unconfirmed')).toBeVisible();
  });

  it('preserves unknown counts for every group when the source is partial', () => {
    const { container } = show('truncated');
    expect(container.querySelector('.current-todo-callout')).not.toHaveTextContent('Show current work.');
    for (const name of ['Other open tasks', 'Checked tasks', 'Deferred tasks']) {
      expect(within(screen.getByRole('group', { name })).getByText('unavailable')).toBeVisible();
    }
  });

  it('retains declared packet deferral when the TODO source is also incomplete', () => {
    const { container } = show('deferred-truncated');
    const deferred = screen.getByRole('group', { name: 'Deferred tasks' });
    expect(deferred).toHaveTextContent('Show current work.');
    expect(deferred).toHaveTextContent('Check the visible behavior.');
    expect(within(deferred).getByText('unavailable')).toBeVisible();
    expect(screen.getByRole('group', { name: 'Other open tasks' })).not.toHaveTextContent('Check the visible behavior.');
    expect(container.querySelector('.current-todo-callout')).not.toHaveTextContent('Show current work.');
  });

  it.each(['ko', 'ja', 'zh-CN'] as const)('explains deferral in %s without translating authored tasks', locale => {
    show('normal', locale);
    const deferred = screen.getByRole('group', { name: workChecklistCopy[locale].deferred });
    expect(deferred).toHaveTextContent(workChecklistCopy[locale].deferredNote);
    expect(deferred).toHaveTextContent('Keep the deferred experiment.');
  });
});
