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
    expect(currentControlStage(closed)).toMatchObject({ status: "undeclared", id: null });
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

  it("labels missing state as unobserved and a failed Doctor result as failed", () => {
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
    expect(signals.find((signal) => signal.id === "verify")?.status).toBe("failed");
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
