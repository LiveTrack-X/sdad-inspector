import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider, useI18n } from '../i18n';
import { selectionFor } from '../selection';
import { packetWorkItems } from '../packetWork';
import { liveDocumentsFixture as docs, snapshotFixture as snapshot } from '../test/fixture';
import type { LiveDocuments, Snapshot } from '../types';
import { Overview } from './Overview';
import { TargetCorrection, TargetCorrectionProvider } from './TargetCorrection';
import type { InteractionRecord } from '../interactions';
import { targetCorrectionCopy } from '../targetCorrectionCopy';

beforeEach(() => {
  localStorage.clear(); Object.defineProperty(navigator,'languages',{configurable:true,value:['en']});
  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:vi.fn().mockResolvedValue(undefined)}});
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({project_root:snapshot.project.root,drafts:[]}))));
});
const source = `${snapshot.protocol.todo_path}:5`;
function fixture(s:Snapshot=snapshot,d:LiveDocuments=docs,visible=true,before='Build the live workspace.') {
  return <I18nProvider><TargetCorrectionProvider snapshot={s} documents={d}>{visible && <TargetCorrection source={source} before={before}/>}</TargetCorrectionProvider></I18nProvider>;
}
function open() {fireEvent.click(screen.getByText('Correct this item',{selector:'summary'}));}
function type(text='Keep the saved value after restart.') {fireEvent.change(screen.getByRole('textbox'),{target:{value:text}});}

describe('source-targeted correction copy', () => {
  it('copies the selected item and source with project context and no fabricated request linkage',async () => {
    render(fixture());open();type();
    fireEvent.click(screen.getByRole('button',{name:'Copy correction request'}));
    expect(await screen.findByText('Copied · delivery unconfirmed')).toBeVisible();
    const text = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
    for(const value of [source,snapshot.project.root,snapshot.state.active_packet!.id,'Build the live workspace.','Keep the saved value after restart.',docs.read_at]) expect(text).toContain(value);
    expect(text).not.toContain('Correction ID:');
    expect(fetch).not.toHaveBeenCalled();
  });
  it('retains input through navigation and isolates projects and changed source revisions', () => {
    const view=render(fixture());open();type();
    view.rerender(fixture(snapshot,docs,false));view.rerender(fixture());open();
    expect(screen.getByRole('textbox')).toHaveValue('Keep the saved value after restart.');
    const other={...snapshot,project:{...snapshot.project,root:'C:/other'}};
    view.rerender(fixture(other,{...docs,project_root:other.project.root}));open();
    expect(screen.getByRole('textbox')).toHaveValue('');
    view.rerender(fixture());open();expect(screen.getByRole('textbox')).toHaveValue('Keep the saved value after restart.');
    const changed={...docs,documents:docs.documents.map(d=>d.path===snapshot.protocol.todo_path?{...d,sha256:'new-revision'}:d)};
    view.rerender(fixture(snapshot,changed));open();expect(screen.getByRole('textbox')).toHaveValue('');
  });
  it.each(['stale','other-project','missing','truncated'] as const)('blocks copy for %s evidence',kind => {
    const s=kind==='stale'?{...snapshot,inspection_status:'stale' as const}:snapshot;
    const d=kind==='other-project'?{...docs,project_root:'C:/other'}:kind==='missing'?{...docs,documents:[]}:kind==='truncated'?{...docs,documents:docs.documents.map(d=>({...d,truncated:true}))}:docs;
    render(fixture(s,d));open();type();expect(screen.getByRole('button',{name:'Copy correction request'})).toBeDisabled();
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
  });
  it('keeps failed clipboard text editable without a copied claim',async () => {
    vi.mocked(navigator.clipboard.writeText).mockRejectedValue(new Error('denied'));
    render(fixture());open();type();fireEvent.click(screen.getByRole('button',{name:'Copy correction request'}));
    expect(await screen.findByText('Copy failed. Your text is retained.')).toBeVisible();
    expect(screen.getByRole('textbox')).toHaveValue('Keep the saved value after restart.');
    expect(screen.queryByText('Copied · delivery unconfirmed')).not.toBeInTheDocument();
  });
  it.each(['ko','ja','zh-CN'] as const)('localizes the correction action and copied context in %s',async locale => {
    Object.defineProperty(navigator,'languages',{configurable:true,value:[locale]});
    const c=targetCorrectionCopy[locale]; render(fixture());
    fireEvent.click(screen.getByText(c.open,{selector:'summary'}));type();
    fireEvent.click(screen.getByRole('button',{name:c.copy}));
    expect(await screen.findByText(c.copied)).toBeVisible();
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain(`${c.source}: ${source}`);
  });
});

function Entry() {
  const {t}=useI18n();
  const r:InteractionRecord={version:1,id:'request',kind:'request',packet:snapshot.state.active_packet!.id,request_id:'settings',base_revision:'r1',author:'test',reported_at:'2026-09-13T00:00:00Z',summary:'Preserve account preferences.',source_ref:'SPEC/SPEC-COMPLETE.md',link_status:'matched',source:{path:'docs/implementation-notes.md',line:1,sha256:'x'}};
  const documents:LiveDocuments={...docs,interactions:{schema_version:1,project_root:snapshot.project.root,packet:r.packet,observed_at:'now',status:'available',records:[r,{...r,id:'interpretation',kind:'interpretation',summary:'Save in this browser.'}],issues:[]}};
  const work=packetWorkItems(docs.documents.find(d=>d.path===snapshot.protocol.todo_path)!.content!,r.packet);
  return <Overview snapshot={snapshot} selectedId="overview" selection={selectionFor(snapshot,'overview',t)} busy={false} progress={null} liveDocuments={documents} activity={null} packetWork={work} rule5={null} onSelect={vi.fn()}/>;
}
it('exposes request comparison immediately on Overview and connects the declared objective to correction copy',async () => {
  render(<I18nProvider><Entry/></I18nProvider>);
  const panel=screen.getByRole('region',{name:'My request and AI understanding'});
  expect(within(panel).getByText('Preserve account preferences.',{selector:'p'})).toBeVisible();
  expect(within(panel).getByText('Save in this browser.')).toBeVisible();
  const objective=screen.getByRole('region',{name:snapshot.state.active_packet!.id});
  fireEvent.click(within(objective).getByText('Correct this item',{selector:'summary'}));
  fireEvent.change(within(objective).getByRole('textbox'),{target:{value:'Make the request comparison primary.'}});
  fireEvent.click(within(objective).getByRole('button',{name:'Copy correction request'}));
  await waitFor(()=>expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
  expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('sdad-state.yaml#active_packet.objective');
});
