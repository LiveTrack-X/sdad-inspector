import { describe, expect, it } from "vitest";
import {
  classifyWorktreePath,
  conditionalBranchSignals,
  controlLoopSignals,
  currentControlStage,
  worktreeLensSignals,
} from "./developmentStages";
import { packetWorkItems } from "./packetWork";
import { activityFixture, liveDocumentsFixture, snapshotFixture } from "./test/fixture";

describe("official SDAD control-loop evidence", () => {
  it.each([
    ["sdad-state.yaml", "control"],
    ["SPEC/SPEC-COMPLETE.md", "control"],
    ["src/feature.ts", "implementation"],
    ["tests/test_feature.py", "verification"],
    ["scripts/validate_repo.py", "verification"],
    ["docs/evidence-matrix.md", "evidence"],
    ["review-findings.md", "evidence"],
    ["docs/handoffs/progress.md", "documentation"],
  ])("classifies %s in the secondary %s lens", (path, lens) => {
    expect(classifyWorktreePath(path)).toBe(lens);
  });

  it("uses the exact official order and never infers a current stage from timestamps", () => {
    const signals = controlLoopSignals(snapshotFixture, liveDocumentsFixture, activityFixture);
    expect(signals.map((signal) => signal.id)).toEqual(["plan", "route", "implement", "verify", "report"]);
    expect(signals.map((signal) => signal.status)).not.toContain("current");
    expect(signals.find((signal) => signal.id === "implement")).toMatchObject({
      status: "observed",
      observedCount: 2,
    });
  });

  it("highlights a stage only from an explicit open current TODO marker", () => {
    const declared = packetWorkItems(
      "## Active Work\n\n- [ ] [packet:demo] [current] [phase:Implement] Build it.",
      "demo",
    );
    const generic = packetWorkItems(
      "## Active Work\n\n- [ ] [packet:demo] Build it.",
      "demo",
    );
    const closed = packetWorkItems(
      "## Active Work\n\n- [x] [packet:demo] [current] [phase:Verify] Test it.",
      "demo",
    );

    expect(currentControlStage(declared)).toMatchObject({ status: "declared", id: "implement", itemCount: 1 });
    expect(currentControlStage(generic)).toMatchObject({ status: "undeclared", id: null });
    expect(currentControlStage(closed)).toMatchObject({ status: "idle", id: null });
  });

  it.each([
    ["empty", ""],
    ["completed", "## Active Work\n- [x] [packet:demo] [current] [phase:Verify] Done."],
    ["deferred", "## Future / Deferred\n- [ ] [packet:demo] [current] [phase:Implement] Resume only by request."],
  ])("keeps %s work idle without claiming passed verification", (_kind, markdown) => {
    expect(currentControlStage(packetWorkItems(markdown,"demo"))).toEqual({status:"idle",id:null,itemCount:0,sourcePath:"docs/TODO-Open-Items.md"});
  });

  it("keeps unresolved work outside known deferred sections active", () => {
    const work=packetWorkItems("## Future / Deferred\n- [ ] [packet:demo] [current] [phase:Verify] Old marker.\n## Needs decision\n- [ ] [packet:demo] Decide.","demo");
    expect(currentControlStage(work)).toMatchObject({status:"undeclared",id:null});
  });

  it.each(["[current]", "[current] [phase:Unknown]", "[current] [phase:Plan] [phase:Verify]"])("does not guess an unknown or invalid current phase: %s", markers => {
    const work=packetWorkItems(`## Active Work\n- [ ] [packet:demo] ${markers} Work.`,"demo");
    expect(currentControlStage(work)).toMatchObject({status:"ambiguous",id:null});
  });

  it.each(["missing-documents", "wrong-project", "missing-todo", "truncated", "unreadable", "stale", "missing-state", "missing-packet"])("reports %s as unavailable rather than idle or current", kind => {
    const base=snapshotFixture;
    const snapshot=kind==="stale"?{...base,inspection_status:"stale" as const}:kind==="missing-state"?{...base,state:{...base.state,available:false}}:kind==="missing-packet"?{...base,state:{...base.state,active_packet:null}}:base;
    const docs=liveDocumentsFixture;
    const documents=kind==="missing-documents"?null:kind==="wrong-project"?{...docs,project_root:"elsewhere"}:kind==="missing-todo"?{...docs,documents:[]}:kind==="truncated"?{...docs,documents:docs.documents.map(d=>({...d,truncated:true}))}:kind==="unreadable"?{...docs,documents:docs.documents.map(d=>({...d,error:{code:"failed",message:"unreadable"}}))}:docs;
    const item=packetWorkItems(`## Active Work\n- [ ] [packet:${base.state.active_packet!.id}] [current] [phase:Implement] Work.`,base.state.active_packet!.id)[0];
    expect(currentControlStage([item],base.protocol.todo_path,{snapshot,documents})).toMatchObject({status:"unavailable",id:null});
  });

  it.each(["\n", "\n\n"])("finds later current work and conflicting phases in a complete ledger with separator %j", separator => {
    const snapshot=snapshotFixture;
    const packet=snapshot.state.active_packet!.id;
    const closed=Array.from({length:40},(_,index)=>`- [x] [packet:${packet}] Completed ${index+1}.`);
    const classify=(rows:string[])=>{
      const markdown=`## Active Work\n${rows.join(separator)}`;
      const documents={...liveDocumentsFixture,documents:liveDocumentsFixture.documents.map(d=>d.path===snapshot.protocol.todo_path?{...d,content:markdown}:d)};
      return currentControlStage(packetWorkItems(markdown,packet),snapshot.protocol.todo_path,{snapshot,documents});
    };
    expect(classify(closed)).toMatchObject({status:"idle",id:null});
    const current=[...closed,`- [ ] [packet:${packet}] [current] [phase:Implement] Current task.`];
    expect(classify(current)).toMatchObject({status:"declared",id:"implement",itemCount:1});
    expect(classify([...current,`- [ ] [packet:${packet}] [current] [phase:Verify] Conflicting task.`])).toMatchObject({status:"ambiguous",id:null,itemCount:2});
  });

  it("does not activate example markers or nested deferred markers",()=>{
    const markdown=["## Future / Deferred","### Waiting for owner","- [ ] [packet:demo] [current] [phase:Implement] Not reactivated.","## Active Work","~~~markdown","- [ ] [packet:demo] [current] [phase:Verify] Example only.","~~~","- [ ] [packet:demo] Actual unselected work."].join("\n");
    expect(currentControlStage(packetWorkItems(markdown,"demo"))).toMatchObject({status:"undeclared",id:null,itemCount:0});
  });

  it("does not reactivate a deferred packet from an old current marker", () => {
    const snapshot={...snapshotFixture,state:{...snapshotFixture.state,active_packet:{...snapshotFixture.state.active_packet!,status:"deferred"}}};
    const work=packetWorkItems(`## Active Work\n- [ ] [packet:${snapshot.state.active_packet.id}] [current] [phase:Implement] Work.`,snapshot.state.active_packet.id);
    expect(currentControlStage(work,snapshot.protocol.todo_path,{snapshot,documents:liveDocumentsFixture})).toMatchObject({status:"deferred",id:null});
  });

  it("does not choose a stage when explicit current markers conflict", () => {
    const work = packetWorkItems(
      [
        "## Active Work",
        "",
        "- [ ] [packet:demo] [current] [phase:Implement] Build it.",
        "- [ ] [packet:demo] [current] [phase:Verify] Test it.",
      ].join("\n"),
      "demo",
    );

    expect(currentControlStage(work)).toMatchObject({ status: "ambiguous", id: null, itemCount: 2 });
  });

  it("separates eligible routes from files read by this Inspector scan", () => {
    const signals = controlLoopSignals(snapshotFixture, liveDocumentsFixture, activityFixture);
    expect(signals.find((signal) => signal.id === "route")).toMatchObject({
      status: "observed",
      declaredCount: 3,
      observedCount: 3,
    });

    const withoutDocuments = controlLoopSignals(snapshotFixture, null, activityFixture);
    expect(withoutDocuments.find((signal) => signal.id === "route")).toMatchObject({
      status: "declared",
      declaredCount: 3,
      observedCount: 0,
    });
  });

  it("keeps declared validation unverified even when Doctor structural checks pass", () => {
    const verify = controlLoopSignals(snapshotFixture, liveDocumentsFixture, activityFixture)
      .find((signal) => signal.id === "verify");
    expect(verify).toMatchObject({
      status: "unverified",
      declaredCount: 2,
      observedCount: 0,
      verifiedCount: 1,
    });
  });

  it("never upgrades absent execution evidence to verified when no commands are declared",()=>{
    const snapshot={...snapshotFixture,state:{...snapshotFixture.state,validation:[]}};
    const verify=controlLoopSignals(snapshot,liveDocumentsFixture,null).find(signal=>signal.id==="verify");
    expect(verify).toMatchObject({status:"unobserved",declaredCount:0,observedCount:0,verifiedCount:1});
    expect(verify?.sourcePaths).toContain("Doctor JSON");
  });

  it("supports a normalized state-schema-1 snapshot without changing the control loop", () => {
    const stateV1 = {
      ...snapshotFixture,
      contracts: { ...snapshotFixture.contracts, state_schema_version: 1 },
      doctor: { ...snapshotFixture.doctor, state_schema_version: 1 },
      state: {
        ...snapshotFixture.state,
        schema_version: 1,
        execution_scope: null,
        legacy_controls: { intensity: "standard", autonomy: 1 },
      },
    };
    expect(controlLoopSignals(stateV1, liveDocumentsFixture, activityFixture).map((signal) => signal.id))
      .toEqual(["plan", "route", "implement", "verify", "report"]);
  });

  it("keeps missing-state diagnostics unobserved while preserving genuine completed Doctor failure", () => {
    const missingState = {
      ...snapshotFixture,
      inspection_status: "diagnostic",
      contracts: { ...snapshotFixture.contracts, state_schema_version: null },
      doctor: {
        ...snapshotFixture.doctor,
        state_schema_version: null,
        exit_code: 1,
        summary: { errors: 1, warnings: 0 },
      },
      state: {
        ...snapshotFixture.state,
        available: false,
        schema_version: null,
        active_spec: null,
        active_packet: null,
        validation: [],
        owner_gates: [],
        routed_docs: [],
        current_handoff: null,
      },
    } as typeof snapshotFixture;
    const signals = controlLoopSignals(missingState, null, null);
    expect(signals.find((signal) => signal.id === "plan")?.status).toBe("unobserved");
    expect(signals.find((signal) => signal.id === "route")?.status).toBe("unobserved");
    expect(signals.find((signal) => signal.id === "verify")).toMatchObject({status:"unobserved",verifiedCount:0});
    const completedFailure={...missingState,inspection_status:"completed"};
    expect(controlLoopSignals(completedFailure,null,null).find(signal=>signal.id==="verify")?.status).toBe("failed");
    expect(conditionalBranchSignals(missingState, null, null).map((branch) => branch.status))
      .toEqual(["not_applicable", "not_applicable"]);
  });

  it("keeps Owner Gate and Handoff as conditional branches", () => {
    const branches = conditionalBranchSignals(snapshotFixture, liveDocumentsFixture, activityFixture);
    expect(branches).toEqual([
      expect.objectContaining({ id: "owner_gate", status: "declared", declaredCount: 4, observedCount: 0 }),
      expect.objectContaining({ id: "handoff", status: "not_applicable" }),
    ]);
  });

  it("keeps worktree classification secondary and non-causal", () => {
    const lenses = worktreeLensSignals(activityFixture);
    expect(lenses.find((lens) => lens.id === "implementation")?.paths).toEqual(["web/src/App.tsx"]);
    expect(lenses.find((lens) => lens.id === "documentation")?.paths).toEqual(["docs/handoff.md"]);
  });
});
