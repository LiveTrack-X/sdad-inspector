import type { ActivityFile, DevelopmentActivity, Snapshot } from "./types";

export type DevelopmentStageId = "scope" | "build" | "verify" | "evidence" | "docs";
export type DevelopmentStageStatus = "current" | "observed" | "declared" | "none";

export interface DevelopmentStageSignal {
  id: DevelopmentStageId;
  status: DevelopmentStageStatus;
  changedCount: number;
  latestPath: string | null;
  currentBasis: string | null;
}

const STAGES: DevelopmentStageId[] = ["scope", "build", "verify", "evidence", "docs"];

export function classifyDevelopmentPath(path: string): DevelopmentStageId {
  const normalized = path.replaceAll("\\", "/").toLocaleLowerCase();
  const basename = normalized.split("/").at(-1) ?? normalized;
  if (
    normalized === "sdad-state.yaml"
    || normalized.startsWith("spec/")
    || basename === "todo-open-items.md"
    || basename === "next-task.md"
    || basename === "implementation-notes.md"
  ) return "scope";
  if (
    normalized.startsWith("tests/")
    || normalized.includes("/__tests__/")
    || /(^|\/)(test_|spec_)/.test(normalized)
    || /\.(test|spec)\.[^.]+$/.test(normalized)
    || /(^|[\/_-])(verify|validate|validator|check|smoke)([-_.\/]|$)/.test(normalized)
  ) return "verify";
  if (
    normalized.includes("evidence")
    || normalized.includes("claim-registry")
    || normalized.includes("review-findings")
    || normalized.includes("design-qa")
    || normalized.includes("report")
  ) return "evidence";
  if (
    normalized.startsWith("docs/")
    || normalized.includes("handoff")
    || basename.startsWith("readme")
    || basename.startsWith("changelog")
  ) return "docs";
  return "build";
}

function timestamp(file: ActivityFile): number {
  if (!file.modified_at) return Number.NEGATIVE_INFINITY;
  const value = Date.parse(file.modified_at);
  return Number.isFinite(value) ? value : Number.NEGATIVE_INFINITY;
}

export function developmentStageSignals(
  snapshot: Snapshot,
  activity: DevelopmentActivity | null,
): DevelopmentStageSignal[] {
  const files = activity?.files ?? [];
  const grouped = new Map<DevelopmentStageId, ActivityFile[]>(STAGES.map((id) => [id, []]));
  for (const file of files) grouped.get(classifyDevelopmentPath(file.path))?.push(file);

  const latest = files.reduce<ActivityFile | null>((current, file) => {
    if (!current || timestamp(file) > timestamp(current)) return file;
    return current;
  }, null);
  const currentStage = latest && timestamp(latest) !== Number.NEGATIVE_INFINITY
    ? classifyDevelopmentPath(latest.path)
    : null;

  return STAGES.map((id) => {
    const observed = grouped.get(id) ?? [];
    const latestForStage = observed.reduce<ActivityFile | null>((current, file) => {
      if (!current || timestamp(file) > timestamp(current)) return file;
      return current;
    }, null);
    const declared = id === "scope"
      ? Boolean(snapshot.state.active_packet || snapshot.state.active_spec)
      : id === "verify" && snapshot.state.validation.length > 0;
    const status: DevelopmentStageStatus = currentStage === id
      ? "current"
      : observed.length > 0
        ? "observed"
        : declared
          ? "declared"
          : "none";
    return {
      id,
      status,
      changedCount: observed.length,
      latestPath: latestForStage?.path ?? null,
      currentBasis: currentStage === id ? latest?.path ?? null : null,
    };
  });
}
