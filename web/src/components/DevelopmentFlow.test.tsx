import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n';
import { packetWorkItems } from '../packetWork';
import { liveDocumentsFixture, snapshotFixture } from '../test/fixture';
import type { LiveDocuments, Snapshot } from '../types';
import { DevelopmentFlowView } from './DevelopmentFlow';

vi.mock('./InteractionPanel',()=>({InteractionPanel:()=>null}));
beforeEach(()=>{
  localStorage.clear();
  Object.defineProperty(navigator,'languages',{configurable:true,value:['en']});
});
const packet=snapshotFixture.state.active_packet!.id;
function show(markdown:string,snapshot:Snapshot=snapshotFixture,unavailable=false) {
  const documents:LiveDocuments|null=unavailable?null:{...liveDocumentsFixture,documents:liveDocumentsFixture.documents.map(d=>d.path===snapshot.protocol.todo_path?{...d,content:markdown}:d)};
  return render(<I18nProvider><DevelopmentFlowView snapshot={snapshot} documents={documents} activity={null} work={packetWorkItems(markdown,packet)} onSelect={vi.fn()}/></I18nProvider>);
}

describe('current work orientation',()=>{
  it.each([
    ['empty','## Active Work\n'],
    ['completed',`## Active Work\n- [x] [packet:${packet}] [current] [phase:Verify] Test it.`],
    ['deferred items',`## Future / Deferred\n- [ ] [packet:${packet}] [current] [phase:Implement] Future task.`],
  ])('shows %s as no active TODO without claiming completion or requesting marker repair',(_name,markdown)=>{
    const {container}=show(markdown);
    const situation=screen.getByRole('region',{name:/No active TODO is observed/});
    expect(within(situation).getByRole('heading')).toHaveTextContent('This does not establish completion, passed verification, or owner acceptance.');
    expect(within(situation).getByText(/Add a current marker only when authorized work actually starts/)).toBeVisible();
    expect(within(situation).queryByText(/mark the actual current TODO/)).not.toBeInTheDocument();
    expect(container.querySelector('[aria-current="step"]')).toBeNull();
    if(markdown.includes('Future task')) expect(screen.getByText('Future task.',{selector:'summary span'})).toBeVisible();
  });

  it('distinguishes open but unselected work from idle work',()=>{
    const {container}=show(`## Active Work\n- [ ] [packet:${packet}] Build it.`);
    expect(screen.getByRole('heading',{name:/has open work, but no current TODO is selected/})).toBeVisible();
    expect(screen.queryByRole('heading',{name:/No active TODO is observed/})).not.toBeInTheDocument();
    expect(container.querySelector('[aria-current="step"]')).toBeNull();
  });

  it('distinguishes unavailable evidence from no work even when old current items remain',()=>{
    const {container}=show(`## Active Work\n- [ ] [packet:${packet}] [current] [phase:Implement] Old item.`,snapshotFixture,true);
    expect(screen.getByRole('heading',{name:/Current-work evidence.*unavailable or incomplete/})).toBeVisible();
    expect(screen.getAllByText('Current work cannot be determined from this scan.').length).toBeGreaterThan(0);
    expect(screen.queryByRole('heading',{name:/No active TODO is observed/})).not.toBeInTheDocument();
    expect(container.querySelector('[aria-current="step"]')).toBeNull();
    expect(screen.getByText('Old item.',{selector:'summary span'})).toBeVisible();
    fireEvent.click(screen.getByText('Old item.',{selector:'summary span'}));
    expect(screen.getByText('Recorded [current] marker; active work unconfirmed')).toBeVisible();
    expect(screen.queryByText('Current task')).not.toBeInTheDocument();
  });

  it('preserves deferred packet work without treating its old marker as reactivation',()=>{
    const snapshot={...snapshotFixture,state:{...snapshotFixture.state,active_packet:{...snapshotFixture.state.active_packet!,status:'deferred'}}};
    const {container}=show(`## Active Work\n- [ ] [packet:${packet}] [current] [phase:Implement] Wait for owner.`,snapshot);
    expect(screen.getByRole('heading',{name:/explicitly deferred.*Old current markers do not reactivate/})).toBeVisible();
    expect(screen.getByText('Wait for owner.',{selector:'summary span'})).toBeVisible();
    fireEvent.click(screen.getByText('Wait for owner.',{selector:'summary span'}));
    expect(screen.getByText('Recorded [current] marker; active work unconfirmed')).toBeVisible();
    expect(screen.queryByText('Current task')).not.toBeInTheDocument();
    expect(container.querySelector('[aria-current="step"]')).toBeNull();
  });

  it.each([
    ['ko','활성 TODO가 관찰되지 않았습니다'],
    ['ja','アクティブなTODOは観察されていません'],
    ['zh-CN','未观察到数据包'],
  ])('localizes idle guidance in %s',(locale,text)=>{
    Object.defineProperty(navigator,'languages',{configurable:true,value:[locale]});
    show('## Active Work\n');
    expect(screen.getByRole('heading',{name:new RegExp(text)})).toBeVisible();
    expect(screen.queryByText(/situationStatusIdle/)).not.toBeInTheDocument();
  });
});
