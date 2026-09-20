import { describe, expect, it } from "vitest";
import { packetWorkItems, packetWorkSource } from "./packetWork";
import { liveDocumentsFixture, snapshotFixture } from "./test/fixture";
import type { LiveDocuments, Snapshot } from "./types";

describe("packet work source completeness",()=>{
  it("treats a fully read empty TODO as known zero",()=>{
    const documents={...liveDocumentsFixture,documents:liveDocumentsFixture.documents.map(d=>d.path===snapshotFixture.protocol.todo_path?{...d,content:""}:d)};
    const source=packetWorkSource(snapshotFixture,documents);
    expect(source.complete).toBe(true);
    expect(packetWorkItems(source.document?.content,snapshotFixture.state.active_packet!.id)).toEqual([]);
  });

  it.each(["missing-snapshot","missing-documents","different-project","missing-todo","nonexistent","null-content","error","truncated","stale","diagnostic","missing-state","missing-packet"])("keeps %s totals unknown",kind=>{
    const s=snapshotFixture,d=liveDocumentsFixture;
    let snapshot:Snapshot|null=s;
    let documents:LiveDocuments|null=d;
    if(kind==="missing-snapshot") snapshot=null;
    if(kind==="missing-documents") documents=null;
    if(kind==="different-project") documents={...d,project_root:"another-project"};
    if(kind==="missing-todo") documents={...d,documents:[]};
    if(["nonexistent","null-content","error","truncated"].includes(kind)) documents={...d,documents:d.documents.map(doc=>doc.path===s.protocol.todo_path?{...doc,...kind==="nonexistent"?{exists:false}:kind==="null-content"?{content:null}:kind==="error"?{error:{code:"unreadable",message:"unreadable"}}:{truncated:true}}:doc)};
    if(kind==="stale" || kind==="diagnostic") snapshot={...s,inspection_status:kind};
    if(kind==="missing-state") snapshot={...s,state:{...s.state,available:false}};
    if(kind==="missing-packet") snapshot={...s,state:{...s.state,active_packet:null}};
    expect(packetWorkSource(snapshot,documents).complete).toBe(false);
    if(kind==="different-project") expect(packetWorkSource(snapshot,documents).document).toBeNull();
    if(kind==="truncated") expect(packetWorkSource(snapshot,documents).document?.content).toBe(d.documents.find(doc=>doc.path===s.protocol.todo_path)!.content);
  });
});

describe("packetWorkItems", () => {
  it("parses explicit current-phase metadata without displaying marker syntax", () => {
    const work = packetWorkItems(
      "## Active Work\n\n- [ ] [packet:demo] [phase:Implement] [current] Build the exact view.\n  Keep the continuation.",
      "demo",
    );

    expect(work).toEqual([{
      completed: false,
      current: true,
      packetId: "demo",
      phase: "implement",
      phaseConflict: false,
      section: "Active Work",
      sectionPath: ["Active Work"],
      text: "Build the exact view. Keep the continuation.",
      summary: "Build the exact view.",
      detail: "Build the exact view.\nKeep the continuation.",
      line: 3,
    }]);
  });

  it("keeps ordinary bracketed task copy and rejects invalid or conflicting phases", () => {
    const work = packetWorkItems(
      [
        "## Active Work",
        "",
        "- [ ] [packet:demo] [frontend] Preserve this label.",
        "- [ ] [packet:demo] [current] [phase:Plan] [phase:Verify] Ambiguous stage.",
        "- [ ] [packet:demo] [current] [phase:Build] Unsupported stage.",
      ].join("\n"),
      "demo",
    );

    expect(work[0]).toMatchObject({ text: "[frontend] Preserve this label.", current: false, phase: null, phaseConflict: false });
    expect(work[1]).toMatchObject({ text: "Ambiguous stage.", current: true, phase: "plan", phaseConflict: true });
    expect(work[2]).toMatchObject({ text: "Unsupported stage.", current: true, phase: null, phaseConflict: true });
  });

  it.each([40,41,100])("parses all %s bounded-document items regardless of blank separators", count => {
    const rows=Array.from({length:count},(_,index)=>`- [ ] [packet:demo] Task ${index+1}.`);
    for (const separator of ["\n","\n\n"]) {
      const work=packetWorkItems(`## Active Work\n\n${rows.join(separator)}\n  Keep the final continuation.\n  And this second line.`,"demo");
      expect(work).toHaveLength(count);
      expect(work.at(-1)?.detail).toBe(`Task ${count}.\nKeep the final continuation.\nAnd this second line.`);
    }
  });

  it.each([
    ["backticks","```markdown","```"],
    ["tildes","~~~markdown","~~~"],
    ["indented opener and closer","   ```markdown","   ```"],
    ["longer closer","~~~markdown","~~~~~"],
  ])("excludes %s examples while preserving the real task after the fence",(_name,opening,closing)=>{
    const markdown=["## Active Work",opening,"## Future / Deferred","- [ ] [packet:demo] [current] [phase:Verify] Example only.",closing,"- [ ] [packet:demo] [current] [phase:Implement] Real work."].join("\n");
    expect(packetWorkItems(markdown,"demo")).toEqual([expect.objectContaining({summary:"Real work.",phase:"implement",section:"Active Work",sectionPath:["Active Work"]})]);
  });

  it.each([
    ["short closer","````markdown","```"],
    ["wrong character","~~~markdown","```"],
    ["trailing text","```markdown","``` still inside"],
    ["non-breaking-space suffix","```markdown","```\u00a0"],
    ["unterminated","```markdown",""],
  ])("does not end a fenced example at a %s",(_name,opening,invalidClosing)=>{
    const markdown=["## Active Work",opening,"- [ ] [packet:demo] Example one.",invalidClosing,"- [ ] [packet:demo] [current] [phase:Verify] Still an example."].join("\n");
    expect(packetWorkItems(markdown,"demo")).toEqual([]);
  });

  it("retains nested code in task details without extracting its fake tasks or headings",()=>{
    const markdown=["## Active Work","- [ ] [packet:demo] [current] [phase:Implement] Build it.","  ```markdown","  ## Future / Deferred","  - [ ] [packet:demo] [current] [phase:Verify] Example only.","  ```","  Keep this note after the example.","- [ ] [packet:other] Other packet."].join("\n");
    const work=packetWorkItems(markdown,"demo");
    expect(work).toHaveLength(1);
    expect(work[0]).toMatchObject({summary:"Build it.",phase:"implement",section:"Active Work"});
    expect(work[0].detail).toContain("```markdown\n## Future / Deferred\n- [ ] [packet:demo] [current] [phase:Verify] Example only.\n```\nKeep this note after the example.");
  });

  it("preserves heading ancestry and resets it only when the enclosing section ends",()=>{
    const markdown=["# Tasks","## Future / Deferred","### Waiting for owner","- [ ] [packet:demo] Old work.","## Active Work ##","- [ ] [packet:demo] New work."].join("\n");
    const work=packetWorkItems(markdown,"demo");
    expect(work[0]).toMatchObject({section:"Waiting for owner",sectionPath:["Tasks","Future / Deferred","Waiting for owner"]});
    expect(work[1]).toMatchObject({section:"Active Work",sectionPath:["Tasks","Active Work"]});
  });
});
