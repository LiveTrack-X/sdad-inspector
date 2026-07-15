import type { DevelopmentActivity, LiveDocuments, Snapshot } from "./types";
import type { PacketWorkItem } from "./packetWork";

export type ControlLoopStageId = "plan" | "route" | "implement" | "verify" | "report";
export type ConditionalBranchId = "owner_gate" | "handoff";
export type EvidenceStatus =
  | "declared"
  | "observed"
  | "verified"
  | "failed"
  | "stale"
  | "unverified"
  | "not_applicable"
  | "unobserved";

export interface ControlLoopSignal {
  id: ControlLoopStageId;
  status: EvidenceStatus;
  declaredCount: number;
  observedCount: number;
  verifiedCount: number;
  sourcePaths: string[];
}

export interface ConditionalBranchSignal {
  id: ConditionalBranchId;
  status: EvidenceStatus;
  declaredCount: number;
  observedCount: number;
  sourcePaths: string[];
}

export interface CurrentControlStageSignal {
  status: "declared" | "undeclared" | "ambiguous";
  id: ControlLoopStageId | null;
  itemCount: number;
  sourcePath: string;
}

export type WorktreeLensId = "control" | "implementation" | "verification" | "evidence" | "documentation";

export interface WorktreeLensSignal {
  id: WorktreeLensId;
  changedCount: number;
  paths: string[];
}

export const CONTROL_LOOP: ControlLoopStageId[] = ["plan", "route", "implement", "verify", "report"];
export const WORKTREE_LENSES: WorktreeLensId[] = ["control", "implementation", "verification", "evidence", "documentation"];

export function currentControlStage(work: PacketWorkItem[], todoPath = "docs/TODO-Open-Items.md"): CurrentControlStageSignal {
  const current = work.filter((item) => item.current && !item.completed);
  if (current.length === 0) {
    return { status: "undeclared", id: null, itemCount: 0, sourcePath: todoPath };
  }
  const phases = new Set(current.map((item) => item.phase).filter((phase): phase is ControlLoopStageId => phase !== null));
  if (current.some((item) => item.phaseConflict || item.phase === null) || phases.size !== 1) {
    return { status: "ambiguous", id: null, itemCount: current.length, sourcePath: todoPath };
  }
  return { status: "declared", id: Array.from(phases)[0], itemCount: current.length, sourcePath: todoPath };
}

function unique(paths: Array<string | null | undefined>): string[] {
  return Array.from(new Set(paths.filter((path): path is string => Boolean(path))));
}

function withFreshness(snapshot: Snapshot, status: EvidenceStatus): EvidenceStatus {
  if (status === "failed" || status === "not_applicable" || status === "unobserved") return status;
  return snapshot.inspection_status === "stale" ? "stale" : status;
}

export function classifyWorktreePath(path: string): WorktreeLensId {
  const normalized = path.replaceAll("\\", "/").toLocaleLowerCase();
  const basename = normalized.split("/").at(-1) ?? normalized;
  if (
    normalized === "sdad-state.yaml"
    || normalized.startsWith("spec/")
    || basename === "todo-open-items.md"
    || basename === "next-task.md"
    || basename === "implementation-notes.md"
  ) return "control";
  if (
    normalized.startsWith("tests/")
    || normalized.includes("/__tests__/")
    || /(^|\/)(test_|spec_)/.test(normalized)
    || /\.(test|spec)\.[^.]+$/.test(normalized)
    || /(^|[\/_-])(verify|validate|validator|check|smoke)([-_.\/]|$)/.test(normalized)
  ) return "verification";
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
  ) return "documentation";
  return "implementation";
}

export function worktreeLensSignals(activity: DevelopmentActivity | null): WorktreeLensSignal[] {
  return WORKTREE_LENSES.map((id) => {
    const paths = (activity?.files ?? [])
      .filter((file) => classifyWorktreePath(file.path) === id)
      .map((file) => file.path);
    return { id, changedCount: paths.length, paths };
  });
}

export function controlLoopSignals(
  snapshot: Snapshot,
  documents: LiveDocuments | null,
  activity: DevelopmentActivity | null,
): ControlLoopSignal[] {
  const planSources = unique([
    snapshot.state.available ? snapshot.protocol.state_path : null,
    snapshot.state.active_spec?.path,
  ]);
  const planDeclarations = Number(Boolean(snapshot.state.active_packet)) + Number(Boolean(snapshot.state.active_spec));

  const eligibleRoutes = unique([
    snapshot.state.active_spec?.path,
    ...snapshot.state.routed_docs,
  ]);
  const readRoutes = documents?.documents.filter((document) => (
    eligibleRoutes.includes(document.path)
    && document.exists
    && document.content !== null
  )).map((document) => document.path) ?? [];

  const doctorVerified = snapshot.doctor.completed && snapshot.doctor.exit_code === 0;
  const doctorFailed = snapshot.doctor.completed && snapshot.doctor.exit_code !== 0;
  const declaredValidationCount = snapshot.state.validation.length;
  // The normalized snapshot contract deliberately carries declarations only.
  // Structured execution evidence is not available in this product version.
  const executedValidationCount = 0;

  const statusByStage: Record<ControlLoopStageId, EvidenceStatus> = {
    plan: planDeclarations > 0 ? "declared" : "unobserved",
    route: readRoutes.length > 0 ? "observed" : eligibleRoutes.length > 0 ? "declared" : "unobserved",
    implement: (activity?.files.length ?? 0) > 0 ? "observed" : "unobserved",
    verify: doctorFailed
      ? "failed"
      : declaredValidationCount > executedValidationCount
        ? "unverified"
        : doctorVerified
          ? "verified"
          : "unobserved",
    report: "unobserved",
  };

  return CONTROL_LOOP.map((id) => {
    if (id === "plan") return {
      id,
      status: withFreshness(snapshot, statusByStage[id]),
      declaredCount: planDeclarations,
      observedCount: Number(snapshot.state.available),
      verifiedCount: 0,
      sourcePaths: planSources,
    };
    if (id === "route") return {
      id,
      status: withFreshness(snapshot, statusByStage[id]),
      declaredCount: eligibleRoutes.length,
      observedCount: readRoutes.length,
      verifiedCount: 0,
      sourcePaths: readRoutes,
    };
    if (id === "implement") return {
      id,
      status: withFreshness(snapshot, statusByStage[id]),
      declaredCount: 0,
      observedCount: activity?.files.length ?? 0,
      verifiedCount: 0,
      sourcePaths: (activity?.files ?? []).map((file) => file.path),
    };
    if (id === "verify") return {
      id,
      status: withFreshness(snapshot, statusByStage[id]),
      declaredCount: declaredValidationCount,
      observedCount: executedValidationCount,
      verifiedCount: Number(doctorVerified),
      sourcePaths: unique([snapshot.protocol.state_path, snapshot.doctor.root ? "Doctor JSON" : null]),
    };
    return {
      id,
      status: statusByStage[id],
      declaredCount: 0,
      observedCount: 0,
      verifiedCount: 0,
      sourcePaths: [],
    };
  });
}

export function conditionalBranchSignals(
  snapshot: Snapshot,
  documents: LiveDocuments | null,
  activity: DevelopmentActivity | null,
): ConditionalBranchSignal[] {
  const handoff = snapshot.state.current_handoff;
  const handoffPath = handoff?.path ?? null;
  const handoffObserved = Boolean(
    handoffPath
    && (
      documents?.documents.some((document) => document.path === handoffPath && document.exists)
      || activity?.handoffs.some((record) => record.path === handoffPath)
    )
  );
  return [
    {
      id: "owner_gate",
      status: withFreshness(
        snapshot,
        snapshot.state.owner_gates.length > 0 ? "declared" : "not_applicable",
      ),
      declaredCount: snapshot.state.owner_gates.length,
      observedCount: 0,
      sourcePaths: snapshot.state.owner_gates.length > 0 ? [`${snapshot.protocol.state_path}#owner_gates`] : [],
    },
    {
      id: "handoff",
      status: withFreshness(
        snapshot,
        handoffObserved ? "observed" : handoff?.declared ? "declared" : "not_applicable",
      ),
      declaredCount: Number(Boolean(handoff?.declared)),
      observedCount: Number(handoffObserved),
      sourcePaths: unique([handoffPath]),
    },
  ];
}
