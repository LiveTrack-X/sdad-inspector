import {describe, expect, it} from 'vitest';
import {correctionParent, correctionText, responseState, type Correction, type InteractionRecord} from './interactions';
const draft: Correction = {id:'C2', request_id:'R1', packet:'P1', base_revision:'r1',project_root:'p1', before:'Browser only',correction:'Across devices',supersedes:'C1',copy_state:'copied'};
const response: InteractionRecord = {version:1,id:'A1',kind:'response',request_id:'R1',packet:'P1',base_revision:'r1',author:'agent',reported_at:'now',summary:'Done',correction_id:'C2',stage:'applied',source:{path:'notes.md',line:1,sha256:'x'},link_status:'matched'};
describe('correction identity and claim boundaries', () => {
  it('parent follows explicit selection or unique lineage, never recopy order', () => {
    const first = {...draft,id:'C1',supersedes:''};
    expect(correctionParent([draft,first],null)).toBe('C2');
    expect(correctionParent([first,draft],first)).toBe('C1');
    expect(correctionParent([first,draft,{...draft,id:'C3'}],null)).toBe('');
  });
  it('copy never establishes delivery' , () => expect(responseState(draft,[],false)).toBe('copied'));
  it('late response to an earlier correction never satisfies the newer correction', () => {
    expect(responseState(draft,[{...response,correction_id:'C1'}],false)).toBe('copied');
    expect(responseState(draft,[response],false)).toBe('applied');
  });
  it('other packet, request and revision reports cannot satisfy a correction', () => {
    for (const changed of [{packet:'P2'},{request_id:'R2'},{base_revision:'r2'},{link_status:'stale' as const}]) expect(responseState(draft,[{...response,...changed}],false)).toBe('copied');
  });
  it('incomplete reads and conflicts do not upgrade claims', () => {
    expect(responseState(draft,[response],true)).toBe('unconfirmed');
    expect(responseState(draft,[response,{...response,id:'A2',link_status:'conflict'}],false)).toBe('conflict');
  });
  it('an explicit resulting revision links the original correction across scope updates', () => {
    expect(responseState(draft,[{...response,result_revision:'r2'}],false,'r2')).toBe('applied');
    expect(responseState(draft,[{...response,result_revision:'r2'}],false,'r3')).toBe('stale');
  });
  it('request text retains target, baseline, supersedes and actual correction', () => {
    const text = correctionText(draft);
    for(const value of ['C2','R1','P1','r1','p1','C1','Browser only','Across devices','awaiting AI report']) expect(text).toContain(value);
  });
});
