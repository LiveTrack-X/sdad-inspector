import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n';
import { selectionFor } from '../selection';
import { liveDocumentsFixture, snapshotFixture } from '../test/fixture';
import { Overview } from './Overview';

vi.mock('./InteractionPanel', () => ({ InteractionPanel: () => null }));

beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en'] });
});

function show(status: string, selectedId = 'overview') {
  const snapshot = { ...snapshotFixture, state: { ...snapshotFixture.state,
    active_packet: { ...snapshotFixture.state.active_packet!, status } } };
  render(<I18nProvider><Overview snapshot={snapshot} selectedId={selectedId}
    selection={selectionFor(snapshot, selectedId, (key) => key)} busy={false}
    progress={null} onSelect={vi.fn()} liveDocuments={liveDocumentsFixture}
    activity={null} packetWork={[]} rule5={null}/></I18nProvider>);
  return snapshot;
}

describe('declared status claim boundaries', () => {
  it.each(['overview', 'state'])('explains software verification in %s without claiming command execution', (selectedId) => {
    show('software_verified', selectedId);
    expect(screen.getByText('software_verified')).toBeVisible();
    expect(screen.getByText(/Inspector has not executed them; external conditions and owner acceptance require separate evidence/)).toBeVisible();
    if (selectedId === 'overview') expect(screen.getByText('presented, not executed')).toBeVisible();
  });

  it.each([
    ['ai_complete', /legacy status.*does not establish executed checks/],
    ['deferred', /Old current markers do not resume it; explicit owner reactivation/],
    ['owner_accepted', /Confirm its scope.*status alone does not verify tests or authorize release/],
    ['future_unknown_status', /declared checkpoint, not a progress percentage/],
  ])('preserves %s verbatim while constraining its meaning', (status, meaning) => {
    const snapshot = show(status);
    expect(screen.getByText(status)).toBeVisible();
    expect(screen.getByText(meaning)).toBeVisible();
    const t = (key: string) => key;
    for (const id of ['overview', 'state', 'packet']) {
      expect(selectionFor(snapshot, id, t).observed).toBe(status);
      expect(selectionFor(snapshot, id, t).remediation).toBe(selectionFor(snapshot, 'overview', t).remediation);
    }
    expect(snapshot.state.validation.every((check) => check.executed === false)).toBe(true);
  });

  it.each([
    ['ko', '소프트웨어 검증을 통과했다는 선언입니다.'],
    ['ja', 'ソフトウェア検証の合格を宣言しています。'],
    ['zh-CN', '此状态声明软件检查已通过。'],
  ])('shows the declaration explanation in %s', (locale, meaning) => {
    Object.defineProperty(navigator, 'languages', { configurable: true, value: [locale] });
    show('software_verified');
    expect(screen.getByText((text) => text.startsWith(meaning))).toBeVisible();
  });
});
