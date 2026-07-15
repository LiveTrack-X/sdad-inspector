import { describe, expect, it } from "vitest";
import { classifyDevelopmentPath, developmentStageSignals } from "./developmentStages";
import { activityFixture, snapshotFixture } from "./test/fixture";

describe("development stage evidence", () => {
  it.each([
    ["sdad-state.yaml", "scope"],
    ["SPEC/SPEC-COMPLETE.md", "scope"],
    ["src/feature.ts", "build"],
    ["tests/test_feature.py", "verify"],
    ["scripts/validate_repo.py", "verify"],
    ["docs/evidence-matrix.md", "evidence"],
    ["review-findings.md", "evidence"],
    ["docs/handoffs/progress.md", "docs"],
  ])("classifies %s as %s", (path, stage) => {
    expect(classifyDevelopmentPath(path)).toBe(stage);
  });

  it("marks only the newest timestamped changed-file stage as current", () => {
    const signals = developmentStageSignals(snapshotFixture, {
      ...activityFixture,
      files: [
        { path: "src/feature.ts", previous_path: null, status: " M", kind: "modified", modified_at: "2026-07-15T06:00:00Z" },
        { path: "tests/test_feature.py", previous_path: null, status: " M", kind: "modified", modified_at: "2026-07-15T06:01:00Z" },
        { path: "docs/handoff.md", previous_path: null, status: " M", kind: "modified", modified_at: "2026-07-15T05:59:00Z" },
      ],
    });
    expect(signals.filter((signal) => signal.status === "current")).toEqual([
      expect.objectContaining({ id: "verify", currentBasis: "tests/test_feature.py" }),
    ]);
    expect(signals.find((signal) => signal.id === "build")?.status).toBe("observed");
    expect(signals.find((signal) => signal.id === "docs")?.status).toBe("observed");
  });

  it("does not invent a current stage without file timestamps", () => {
    const signals = developmentStageSignals(snapshotFixture, {
      ...activityFixture,
      files: [{ path: "src/feature.ts", previous_path: null, status: " M", kind: "modified", modified_at: null }],
    });
    expect(signals.some((signal) => signal.status === "current")).toBe(false);
    expect(signals.find((signal) => signal.id === "scope")?.status).toBe("declared");
    expect(signals.find((signal) => signal.id === "verify")?.status).toBe("declared");
  });
});
