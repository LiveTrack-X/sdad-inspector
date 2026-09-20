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
function fixture(s:Snapshot=snapshot,d:LiveDocuments=docs,visible=true,before='Build the live workspace.',targetSource=source) {
  return <I18nProvider><TargetCorrectionProvider snapshot={s} documents={d}>{visible && <TargetCorrection source={targetSource} before={before}/>}</TargetCorrectionProvider></I18nProvider>;
}
function open() {fireEvent.click(screen.getByText('Correct this item',{selector:'summary'}));}
function type(text='Keep the saved value after restart.') {fireEvent.change(screen.getByRole('textbox'),{target:{value:text}});}
const changedDocs=(before='Build the live workspace.') => ({...docs,read_at:'2026-09-20T00:00:00Z',documents:docs.documents.map(d=>d.path===snapshot.protocol.todo_path?{...d,content:d.content?.replace('Build the live workspace.',before) + '\nUnrelated note.',sha256:'new-revision'}:d)});
function previous() {
  const region=screen.getByRole('region',{name:'Previous draft'});
  fireEvent.click(within(region).getByText(/Previous draft 1/,{selector:'summary'}));
  return within(region);
}

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
    const changed=changedDocs();
    view.rerender(fixture(snapshot,changed));open();expect(screen.getByRole('textbox')).toHaveValue('');
    expect(screen.getByRole('region',{name:'Previous draft'})).toBeVisible();
  });
  it('offers an unchanged item draft after unrelated document edits and copies only after explicit carry-forward',async () => {
    const view=render(fixture());open();type();
    view.rerender(fixture(snapshot,changedDocs()));open();
    expect(screen.getByRole('textbox')).toHaveValue('');
    expect(screen.getByRole('button',{name:'Copy correction request'})).toBeDisabled();
    const recovery=previous();
    expect(recovery.getByText('The selected item text is unchanged; other source content or its revision may have changed.')).toBeVisible();
    expect(recovery.getByText('Keep the saved value after restart.')).toBeVisible();
    expect(recovery.getAllByText('Build the live workspace.')).toHaveLength(2);
    fireEvent.click(recovery.getByRole('button',{name:'Use this draft with the current source'}));
    expect(screen.getByRole('textbox')).toHaveValue('Keep the saved value after restart.');
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Copy correction request'}));
    await waitFor(()=>expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
    const copied=vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
    expect(copied).toContain('SHA-256: new-revision');
    expect(copied).toContain('2026-09-20T00:00:00Z');
    expect(copied).not.toContain('Correction ID:');
    view.rerender(fixture());open();
    expect(screen.getByRole('textbox')).toHaveValue('Keep the saved value after restart.');
  });
  it('compares changed item text and preserves a newly typed draft until explicitly cleared', async () => {
    const view=render(fixture());open();type('Original correction.');
    view.rerender(fixture(snapshot,changedDocs('Use a remote store.'),true,'Use a remote store.'));open();
    const recovery=previous();
    expect(recovery.getByText('Build the live workspace.')).toBeVisible();
    expect(recovery.getByText('Use a remote store.')).toBeVisible();
    expect(recovery.getByText(/same source location does not guarantee/)).toBeVisible();
    type('New correction.');
    expect(recovery.getByRole('button',{name:'Use this draft with the current source'})).toBeDisabled();
    expect(screen.getByRole('textbox')).toHaveValue('New correction.');
    type('');
    fireEvent.click(recovery.getByRole('button',{name:'Use this draft with the current source'}));
    expect(screen.getByRole('textbox')).toHaveValue('Original correction.');
    fireEvent.click(screen.getByRole('button',{name:'Copy correction request'}));
    await waitFor(()=>expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
    const copied=vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
    expect(copied).toContain('Use a remote store.');
    expect(copied).not.toContain('Build the live workspace.');
  });
  it('never offers drafts from another project, packet, or item locator', () => {
    const view=render(fixture());open();type();
    const variants:[Snapshot,LiveDocuments,string][]=[
      [{...snapshot,project:{...snapshot.project,root:'C:/other'}},{...docs,project_root:'C:/other'},source],
      [{...snapshot,state:{...snapshot.state,active_packet:{...snapshot.state.active_packet!,id:'another-packet'}}},docs,source],
      [snapshot,docs,`${snapshot.protocol.todo_path}:6`],
      [snapshot,docs,`${snapshot.protocol.state_path}#active_packet.objective`],
    ];
    for(const [s,d,locator] of variants) {
      view.rerender(fixture(s,d,true,'Build the live workspace.',locator));open();
      expect(screen.getByRole('textbox')).toHaveValue('');
      expect(screen.queryByRole('region',{name:'Previous draft'})).not.toBeInTheDocument();
    }
    view.rerender(fixture());open();
    expect(screen.getByRole('textbox')).toHaveValue('Keep the saved value after restart.');
  });
  it('recovers a line-shifted TODO only through explicit document-level comparison',async () => {
    const view=render(fixture());open();type('Keep this correction after a line is inserted.');
    const changed=changedDocs();
    const shifted={...changed,documents:changed.documents.map(d=>d.path===snapshot.protocol.todo_path?{...d,content:`\n${d.content}`} : d)};
    const movedSource=`${snapshot.protocol.todo_path}:6`;
    view.rerender(fixture(snapshot,shifted,true,'Build the live workspace.',movedSource));open();
    expect(screen.getByRole('textbox')).toHaveValue('');
    expect(screen.queryByRole('region',{name:'Previous draft'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Copy correction request'})).toBeDisabled();
    fireEvent.click(screen.getByText('Other saved drafts in this document',{selector:'summary'}));
    const recovery=within(screen.getByRole('region',{name:'Other saved drafts in this document'}));
    fireEvent.click(recovery.getByText(/Previous draft 1/,{selector:'summary'}));
    expect(recovery.getByText(source)).toBeVisible();
    expect(recovery.getByText(movedSource)).toBeVisible();
    expect(recovery.getByText(/no correspondence is assumed/)).toBeVisible();
    expect(screen.getByRole('textbox')).toHaveValue('');
    fireEvent.click(recovery.getByRole('button',{name:'Use this draft with the current source'}));
    fireEvent.click(screen.getByRole('button',{name:'Copy correction request'}));
    await waitFor(()=>expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
    const copied=vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
    expect(copied).toContain(`Source: ${movedSource}`);
    expect(copied).not.toContain(`Source: ${source}`);
    expect(copied).toContain('Keep this correction after a line is inserted.');
    expect(fetch).not.toHaveBeenCalled();
  });
  it('retains previous drafts when a current source becomes stale but blocks recovery and copy', () => {
    const view=render(fixture());open();type();
    view.rerender(fixture({...snapshot,inspection_status:'stale'},changedDocs()));open();
    const recovery=previous();
    expect(recovery.getByText('Keep the saved value after restart.')).toBeVisible();
    expect(recovery.getByRole('button',{name:'Use this draft with the current source'})).toBeDisabled();
    expect(screen.getByRole('button',{name:'Copy correction request'})).toBeDisabled();
    expect(fetch).not.toHaveBeenCalled();
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
