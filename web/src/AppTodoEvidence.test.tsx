import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { I18nProvider } from './i18n';
import { activityFixture, emptyResumeComparisonFixture, liveDocumentsFixture, snapshotFixture } from './test/fixture';
import type { LiveDocuments, Snapshot } from './types';

vi.mock('./components/InteractionPanel',()=>({InteractionPanel:()=>null}));
beforeEach(()=>{
  localStorage.clear();
  Object.defineProperty(navigator,'languages',{configurable:true,value:['en-US']});
  Object.defineProperty(window,'matchMedia',{configurable:true,value:vi.fn().mockReturnValue({matches:false})});
});
function response(value:unknown){return new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});}
function serve(snapshot:Snapshot,documents:LiveDocuments){
  vi.stubGlobal('fetch',vi.fn().mockImplementation(async input=>{
    const path=String(input);
    if(path==='/api/resume-comparison') return response(emptyResumeComparisonFixture);
    if(path==='/api/documents') return response(documents);
    if(path==='/api/activity') return response(activityFixture);
    if(path==='/api/rule5-candidates') return response({source_path:'review-findings.md',source_sha256:'x',candidates:[],error:null});
    if(path==='/api/recent-projects') return response({schema_version:1,recent_projects:[]});
    if(path==='/api/update/check' || path==='/api/update') return response({supported:false,automatic:true,current_version:'0.0.4',state:'unsupported',available_version:null,release_url:null,downloaded_bytes:0,total_bytes:0,checked_at:null,message:'Source mode',error:null});
    return response(snapshot);
  }));
}

describe('TODO totals across Inspector surfaces',()=>{
  it.each(['truncated','missing','different-project','stale','empty'] as const)('keeps %s source totals consistent in sidebar, field details and checklist',async kind=>{
    const snapshot=kind==='stale'?{...snapshotFixture,inspection_status:'stale'}:snapshotFixture;
    const prefix=`## Active Work\n- [x] [packet:${snapshot.state.active_packet!.id}] Checked prefix item.`;
    const base={...liveDocumentsFixture,documents:liveDocumentsFixture.documents.map(d=>d.path===snapshot.protocol.todo_path?{...d,content:kind==='empty'?'':prefix,truncated:kind==='truncated'}:d)};
    const documents=kind==='missing'?{...base,documents:[]}:kind==='different-project'?{...base,project_root:'another-project'}:base;
    serve(snapshot,documents);
    render(<I18nProvider><App/></I18nProvider>);
    await screen.findByRole('heading',{name:snapshot.state.active_packet!.id});
    const tree=screen.getByRole('complementary',{name:'Repository controls'});
    const todo=within(tree).getByTitle('TODO').closest('button')!;
    expect(todo).toBeVisible();
    expect(within(todo).getByTitle(kind==='empty'?'0':'unavailable')).toBeVisible();
    const center=screen.getByRole('main',{name:'Workspace view'});
    if(kind==='truncated' || kind==='stale') {
      expect(within(center).getByText('Checked prefix item.',{selector:'summary span'})).toBeVisible();
      expect(within(center).getByRole('button',{name:'Open remaining work in the full TODO'})).toHaveTextContent('Remaining work unavailable');
      expect(within(center).getByRole('heading',{name:'Checked work unavailable'})).toBeVisible();
    }
    if(kind!=='empty') expect(within(center).getByText(/Task totals are unavailable/)).toBeVisible();
    if(kind==='different-project') expect(within(center).queryByText('Checked prefix item.')).not.toBeInTheDocument();
    fireEvent.click(todo);
    const inspector=screen.getByRole('complementary',{name:'Inspector details'});
    expect(within(inspector).getByText(kind==='empty'?'0 open items':'unavailable',{selector:'.observed-value'})).toBeVisible();
    fireEvent.click(within(tree).getByTitle('TODO (Markdown)').closest('button')!);
    expect(within(inspector).getByText(kind==='empty'?'0 open items':'unavailable',{selector:'.observed-value'})).toBeVisible();
  });
});
