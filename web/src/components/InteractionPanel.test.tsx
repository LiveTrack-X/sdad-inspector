import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {I18nProvider} from '../i18n';
import {snapshotFixture, liveDocumentsFixture} from '../test/fixture';
import type {Correction, InteractionRecord} from '../interactions';
import {InteractionPanel, clearCorrectionSessions} from './InteractionPanel';
const r: InteractionRecord = {version:1,id:'R1',kind:'request',packet:snapshotFixture.state.active_packet!.id,request_id:'settings',base_revision:'r1',author:'agent',reported_at:'2026-09-08T00:00:00Z',summary:'Save settings',source_ref:'User instruction',source:{path:'docs/TODO-Open-Items.md',line:1,sha256:'x'},link_status:'matched'};
const docs = {...liveDocumentsFixture,interactions:{schema_version:1,project_root:snapshotFixture.project.root,packet:r.packet,observed_at:'now',status:'available',records:[r,{...r,id:'I1',kind:'interpretation' as const,summary:'Browser only'}],issues:[]}};
function panel(documents = docs) {return <I18nProvider><InteractionPanel snapshot={snapshotFixture} documents={documents} onSelect={vi.fn()}/></I18nProvider>;}
describe('request to correction interaction', () => {
  beforeEach(() => {
    clearCorrectionSessions(); localStorage.clear(); Object.defineProperty(navigator,'languages',{configurable:true,value:['en']});
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:vi.fn().mockResolvedValue(undefined)}});
    vi.stubGlobal('fetch',vi.fn().mockImplementation(async (_path,init) => new Response(JSON.stringify(init?.body ? JSON.parse(init.body) : {schema_version:1,project_root:snapshotFixture.project.root,drafts:[]}),{status:200})));
  });
  it('edits and copies a stable request, then recognizes only its exact response',async () => {
    const view = render(panel());
    await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Same account on another device'}});
    fireEvent.click(screen.getByRole('button',{name:'Copy request'}));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveAttribute('readonly'));
    const requestText = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0];
    const id = requestText.match(/Correction ID: (.+)/)![1];
    const response = {...r,id:'A1',kind:'response' as const,summary:'Account sync applied',correction_id:id,stage:'applied'};
    view.rerender(panel({...docs,interactions:{...docs.interactions,records:[...docs.interactions.records,{...response,correction_id:'older-id'}]}}));
    expect(screen.queryByText('Account sync applied')).not.toBeInTheDocument();
    view.rerender(panel({...docs,interactions:{...docs.interactions,records:[...docs.interactions.records,response]}}));
    expect(screen.getByText('Account sync applied')).toBeVisible();
    expect(screen.getAllByText(/AI reported application/).length).toBeGreaterThan(0);
  });
  it('clipboard failure retains sealed text and never claims copied',async () => {
    vi.mocked(navigator.clipboard.writeText).mockRejectedValue(new Error('denied'));
    render(panel());await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Cross-device'}});
    fireEvent.click(screen.getByRole('button',{name:'Copy request'}));
    expect(await screen.findByText('Clipboard access failed. Your text is retained; retry copying.')).toBeVisible();
    expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveAttribute('readonly');
    expect(screen.getAllByText(/Copy prepared/).length).toBeGreaterThan(0);
    expect(screen.queryByText('Copied · delivery unconfirmed')).not.toBeInTheDocument();
  });
  it('storage failure after clipboard exposure preserves immutable identity without success claims',async () => {
    let writes = 0;
    vi.mocked(fetch).mockImplementation(async (_path,init) => {
      if (!init?.body) return new Response(JSON.stringify({schema_version:1,project_root:snapshotFixture.project.root,drafts:[]}));
      writes += 1;
      return writes === 1 ? new Response(String(init.body)) : new Response(JSON.stringify({error:{message:'storage unavailable'}}),{status:503});
    });
    render(panel());await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Cross-device'}});
    fireEvent.click(screen.getByRole('button',{name:'Copy request'}));
    expect(await screen.findByText('Could not save or copy. Your text is retained.')).toBeVisible();
    expect(navigator.clipboard.writeText).toHaveBeenCalledOnce();
    expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveAttribute('readonly');
    expect(screen.queryByText('Copied · delivery unconfirmed')).not.toBeInTheDocument();
  });
  it('legacy projects retain an explicit unreported state', () => {
    render(panel({...docs,interactions:{...docs.interactions,records:[],status:'unreported'}}));
    expect(screen.getByText(/No structured report/)).toBeVisible();
    expect(screen.queryByRole('button',{name:'Correct this interpretation'})).not.toBeInTheDocument();
  });
  it('retains unsaved text and identity after opening a source and remounting', async () => {
    const view = render(panel());
    await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Keep this unsaved edit'}});
    const id = screen.getByText(/^correction-[a-f0-9-]+$/).textContent;
    view.unmount(); render(panel());
    expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveValue('Keep this unsaved edit');
    expect(screen.getByText(id!)).toBeVisible();
  });
  it('isolates drafts across requests and projects, then restores the original', async () => {
    const other = {...r,id:'R2',request_id:'second',summary:'Second request'};
    const multi = {...docs,interactions:{...docs.interactions,records:[...docs.interactions.records,other,{...other,id:'I2',kind:'interpretation' as const}]}};
    const view = render(panel(multi));
    await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Original draft'}});
    fireEvent.change(screen.getByRole('combobox',{name:'Request'}),{target:{value:'second'}});
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Second draft'}});
    fireEvent.change(screen.getByRole('combobox',{name:'Request'}),{target:{value:'settings'}});
    expect(screen.getByRole('textbox')).toHaveValue('Original draft');
    view.rerender(<I18nProvider><InteractionPanel snapshot={{...snapshotFixture,project:{...snapshotFixture.project,root:'/other'}}} documents={null} onSelect={vi.fn()}/></I18nProvider>);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    view.rerender(panel(multi));
    expect(screen.getByRole('textbox')).toHaveValue('Original draft');
  });
  it('keeps conflicting edits and recovers under a new identity', async () => {
    vi.mocked(fetch).mockImplementation(async (_path,init) => init?.body ? new Response(JSON.stringify({error:{code:'correction_conflict'}}),{status:409}) : new Response(JSON.stringify({schema_version:1,project_root:snapshotFixture.project.root,drafts:[]})));
    render(panel());
    await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox'),{target:{value:'My concurrent edit'}});
    const oldId = screen.getByText(/^correction-[a-f0-9-]+$/).textContent;
    fireEvent.click(screen.getByRole('button',{name:'Save draft'}));
    fireEvent.click(await screen.findByRole('button',{name:'Continue with a new correction ID'}));
    expect(screen.getByRole('textbox')).toHaveValue('My concurrent edit');
    expect(screen.queryByText(oldId!)).not.toBeInTheDocument();
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
  });
  it('offers capacity recovery without misleading new-ID advice', async () => {
    vi.mocked(fetch).mockImplementation(async (_path, init) => init?.body ? new Response(JSON.stringify({error:{code:'correction_capacity'}}),{status:422}) : new Response(JSON.stringify({schema_version:1,project_root:snapshotFixture.project.root,drafts:[]})));
    render(panel()); await waitFor(() => expect(screen.getByRole('button',{name:'Correct this interpretation'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Correct this interpretation'}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Retained at capacity'}});
    fireEvent.click(screen.getByRole('button',{name:'Save draft'}));
    expect(await screen.findByText(/A new ID does not free capacity/)).toBeVisible();
    expect(screen.queryByRole('button',{name:'Continue with a new correction ID'})).not.toBeInTheDocument();
    expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveValue('Retained at capacity');
  });
  it('preserves newer unsaved text when its saved version is explicitly archived', async () => {
    const row: Correction = {id:'C1',project_root:snapshotFixture.project.root,packet:r.packet,request_id:r.request_id,base_revision:r.base_revision,before:'Browser only',correction:'Saved version',supersedes:'',copy_state:'draft',revision:1};
    let archived = false;
    vi.mocked(fetch).mockImplementation(async (path, init) => {
      const input = init?.body ? JSON.parse(String(init.body)) : {};
      if (String(path).endsWith('/archive')) {archived = true; return new Response(JSON.stringify(row));}
      return new Response(JSON.stringify({schema_version:1,project_root:row.project_root,drafts:input.archived === true ? archived ? [row] : [] : archived ? [] : [row], leaf_id:'C1', has_more:false, usage:{active_count:archived ? 0:1,active_limit:40,active_bytes:100,byte_limit:524288,archived_count:archived?1:0,project_archived_count:archived?1:0}}));
    });
    render(panel());
    fireEvent.click(await screen.findByRole('button',{name:/Saved version/}));
    fireEvent.change(screen.getByRole('textbox',{name:'Your correction'}),{target:{value:'Unsaved newer version'}});
    fireEvent.click(screen.getByText('Manage correction history'));
    fireEvent.click(await screen.findByRole('button',{name:'Archive'}));
    expect(archived).toBe(false);
    fireEvent.click(screen.getByRole('button',{name:'Confirm history action'}));
    await waitFor(() => expect(screen.getByRole('button',{name:'Save draft'})).toBeDisabled());
    expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveValue('Unsaved newer version');
    fireEvent.click(await screen.findByRole('button',{name:'Continue with a new correction ID'}));
    expect(screen.getByRole('textbox',{name:'Your correction'})).toHaveValue('Unsaved newer version');
    expect(screen.getByRole('textbox',{name:'Your correction'})).not.toHaveAttribute('readonly');
    expect(screen.getByText(/Supersedes correction: C1/, {selector:'pre'})).toBeInTheDocument();
  });
  it('shows exact responses for archived records and exports every recovery field', async () => {
    const row: Correction = {id:'C1',project_root:snapshotFixture.project.root,packet:r.packet,request_id:r.request_id,base_revision:r.base_revision,before:'Browser only',correction:'Historical correction',supersedes:'C0',copy_state:'copied',revision:2};
    vi.mocked(fetch).mockImplementation(async (_path, init) => {
      const input = init?.body ? JSON.parse(String(init.body)) : {};
      return new Response(JSON.stringify({schema_version:1,project_root:row.project_root,drafts:input.archived ? [row]:[],leaf_id:'C1',usage:{active_count:0,active_limit:40,active_bytes:35,byte_limit:524288,archived_count:1,project_archived_count:1}}));
    });
    render(panel({...docs,interactions:{...docs.interactions,records:[...docs.interactions.records,{...r,id:'response',kind:'response',correction_id:'C1',stage:'applied',summary:'Archived exact response'},{...r,id:'wrong',kind:'response',correction_id:'other',stage:'applied',summary:'Wrong response'}]}}));
    fireEvent.click(screen.getByText('Manage correction history'));
    await waitFor(() => expect(screen.getByRole('button',{name:'Archived'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Archived'}));
    fireEvent.click(await screen.findByRole('button',{name:'View correction'}));
    expect(screen.getByText('Archived exact response')).toBeVisible();
    expect(screen.queryByText('Wrong response')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Copy recovery JSON'}));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledOnce());
    expect(JSON.parse(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0])).toEqual({schema_version:1,kind:'sdad-correction-export',draft:row});
    fireEvent.change(screen.getByRole('textbox',{name:'Recovery JSON'}),{target:{value:'{ broken'}});
    const calls = vi.mocked(fetch).mock.calls.length;
    fireEvent.click(screen.getByRole('button',{name:'Restore recovery JSON'}));
    expect(await screen.findByText(/export is invalid or too large/)).toBeVisible();
    expect(vi.mocked(fetch).mock.calls.length).toBe(calls);
  });

});
