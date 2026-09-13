import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n';
import { packetWorkItems } from '../packetWork';
import { activityFixture, liveDocumentsFixture, snapshotFixture } from '../test/fixture';
import { workDetailCopy } from '../workDetailCopy';
import { DevelopmentFlowView, PacketEvidencePanel } from './DevelopmentFlow';
import { PlanDetails, WorkItemDetails } from './WorkDetails';

const packet = snapshotFixture.state.active_packet!.id;
const markdown = `## Active Work\n\n- [ ] [packet:${packet}] [current] [phase:Plan] Review the saving plan.\n  - Preserve preferences across sessions.\n  - Ask about conflict resolution.\n- [ ] [packet:${packet}] Implement saved preferences.\n  Keep existing values when saving fails.`;
const work = packetWorkItems(markdown,packet);
const docs = {...liveDocumentsFixture, documents:liveDocumentsFixture.documents.map(doc => doc.path === snapshotFixture.protocol.todo_path ? {...doc,content:markdown} : doc)};

beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(navigator,'languages',{configurable:true,value:['en']});
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({schema_version:1,project_root:snapshotFixture.project.root,drafts:[]}))));
});

describe('plan and task drill-down', () => {
  it('opens Plan details without changing the declared current phase and opens the original source', async () => {
    const user = userEvent.setup(); const onSelect = vi.fn();
    render(<I18nProvider><DevelopmentFlowView snapshot={snapshotFixture} documents={docs} activity={activityFixture} work={work} onSelect={onSelect}/></I18nProvider>);
    const plan = screen.getByRole('button',{name:'Show Plan details'});
    plan.focus(); await user.keyboard('{Enter}');
    expect(plan).toHaveAttribute('aria-expanded','true');
    const panel = screen.getByRole('region',{name:'Plan details'});
    expect(within(panel).getByText(snapshotFixture.state.active_packet!.objective!)).toBeVisible();
    expect(document.querySelector('[aria-current="step"]')).toHaveTextContent('Plan');
    await user.click(within(panel).getByText('Review the saving plan.',{selector:'summary span'}));
    expect(within(panel).getByText('Ask about conflict resolution.')).toBeVisible();
    await user.click(within(panel).getAllByRole('button',{name:'Open full source'})[0]);
    expect(onSelect).toHaveBeenCalledWith('todo');
    await user.click(plan);
    expect(screen.queryByRole('region',{name:'Plan details'})).not.toBeInTheDocument();
    expect(document.querySelector('[aria-current="step"]')).toHaveTextContent('Plan');
  });

  it('reveals continuation text, declared status and source line from an individual task', async () => {
    const user = userEvent.setup(); const onOpen = vi.fn();
    render(<I18nProvider><WorkItemDetails item={work[1]} todoPath={snapshotFixture.protocol.todo_path} onOpenSource={onOpen}/></I18nProvider>);
    expect(screen.getByText(/Keep existing values when saving fails\./)).not.toBeVisible();
    await user.click(screen.getByText('Implement saved preferences.',{selector:'summary span'}));
    expect(screen.getByText(/Keep existing values when saving fails\./)).toBeVisible();
    expect(screen.getByText('Open task')).toBeVisible();
    expect(screen.getByText(`${snapshotFixture.protocol.todo_path}:6`)).toBeVisible();
    await user.click(screen.getByRole('button',{name:'Open full source'}));
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it('opens the full remaining TODO from Overview', async () => {
    const onSelect=vi.fn();
    render(<I18nProvider><PacketEvidencePanel snapshot={snapshotFixture} documents={docs} activity={activityFixture} work={work} onSelect={onSelect}/></I18nProvider>);
    await userEvent.click(screen.getByRole('button',{name:'Open remaining work in the full TODO'}));
    expect(onSelect).toHaveBeenCalledWith('todo');
  });

  it('does not leak another project document or infer missing Plan tasks', () => {
    render(<I18nProvider><PlanDetails snapshot={snapshotFixture} documents={{...docs,project_root:'/different-project',documents:[{path:snapshotFixture.protocol.todo_path,exists:true,roles:['todo'],content:'Other project confidential plan',error:null}]}} work={work} onSelect={vi.fn()}/></I18nProvider>);
    expect(screen.queryByText('Other project confidential plan')).not.toBeInTheDocument();
    expect(screen.queryByText('Review the saving plan.')).not.toBeInTheDocument();
    expect(screen.getByText(/No readable document/)).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('Sources are stale or unavailable');
  });

  it('shows a bounded source read error instead of invented details', async () => {
    const broken = {...docs,documents:[{path:snapshotFixture.protocol.todo_path,exists:true,roles:['todo'],content:null,error:{code:'read_failed',message:'Source unavailable'}}]};
    render(<I18nProvider><PlanDetails snapshot={snapshotFixture} documents={broken} work={[]} onSelect={vi.fn()}/></I18nProvider>);
    await userEvent.click(screen.getByText(snapshotFixture.protocol.todo_path));
    expect(screen.getByRole('alert')).toHaveTextContent('Source unavailable');
    expect(screen.getByText(/No open task is explicitly marked Plan/)).toBeVisible();
  });

  it.each(['ko','ja','zh-CN'] as const)('localizes the new detail controls in %s', async locale => {
    Object.defineProperty(navigator,'languages',{configurable:true,value:[locale]});
    render(<I18nProvider><WorkItemDetails item={work[1]} todoPath={snapshotFixture.protocol.todo_path} onOpenSource={vi.fn()}/></I18nProvider>);
    await userEvent.click(screen.getByText('Implement saved preferences.',{selector:'summary span'}));
    expect(screen.getByRole('button',{name:workDetailCopy[locale].openSource})).toBeVisible();
    expect(screen.getByText(workDetailCopy[locale].remaining)).toBeVisible();
  });
});
