import { InteractionPanel } from "./InteractionPanel";
import { type ReactNode, useId, useState } from "react";
import { PlanDetails, WorkItemDetails } from "./WorkDetails";
import { workDetailCopy } from "../workDetailCopy";
import {
  ArrowRight,
  BookOpenText,
  CheckCircle,
  Clock,
  Cube,
  FileText,
  FlagBanner,
  FunnelSimple,
  GitBranch,
  GitCommit,
  GitDiff,
  Info,
  Lock,
  Shield,
  Stack,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import {
  classifyWorktreePath,
  conditionalBranchSignals,
  CONTROL_LOOP,
  controlLoopSignals,
  currentControlStage,
  worktreeLensSignals,
  type ControlLoopStageId,
  type EvidenceStatus,
  type WorktreeLensId,
} from "../developmentStages";
import { useI18n } from "../i18n";
import type { PacketWorkItem } from "../packetWork";
import { documentSelectionId } from "../selection";
import { formatAbsolute, formatRelative } from "../time";
import type { DevelopmentActivity, LiveDocuments, Snapshot } from "../types";

function TimeLabel({ value }: { value: string | null }) {
  const { locale } = useI18n();
  if (!value) return <span className="time-label">—</span>;
  return <time className="time-label" dateTime={value} title={formatAbsolute(value, locale)}>{formatRelative(value, locale)}</time>;
}

function WorkChecklist({ work, todoPath, onOpenSource, showCurrent = true }: { work: PacketWorkItem[]; todoPath: string; onOpenSource: () => void; showCurrent?: boolean }) {
  const { locale, t } = useI18n();
  const currentItems = work.filter((item) => item.current && !item.completed);
  const open = work.filter((item) => !item.completed && !item.current);
  const completed = work.filter((item) => item.completed);
  const showSections = new Set(work.map((item) => item.section)).size > 1;
  const itemText = (item: PacketWorkItem) => <div><WorkItemDetails item={item} todoPath={todoPath} onOpenSource={onOpenSource}/>{showSections && <small className="todo-source-section">{t("todoSourceSection", { section: item.section })}</small>}</div>;
  return (
    <section className="packet-work" aria-labelledby="packet-work-heading">
      <div className="section-heading-row">
        <h2 id="packet-work-heading">{t("packetTodo")}</h2>
        <span className="source-chip" title={todoPath}>{todoPath}</span>
      </div>
      {!work.length ? <p className="empty-copy">{t("noPacketTaggedWork")}</p> : (
        <>
          {showCurrent && (
            <div className={`current-todo-callout ${currentItems.length ? "declared" : "undeclared"}`}>
              <div className="current-todo-heading"><FlagBanner size={19} /><strong>{t("currentTodo")}</strong><span>{currentItems.length}</span></div>
              {currentItems.length ? <ul>{currentItems.map((item, index) => <li key={index}>{item.phase && !item.phaseConflict && <em>{controlStageLabel(item.phase, t)}</em>}{itemText(item)}</li>)}</ul> : <p>{t("currentTodoUndeclared")}</p>}
            </div>
          )}
          <div className="work-columns">
            <div><h3><button type="button" className="remaining-work-trigger" aria-label={workDetailCopy[locale].openRemaining} onClick={onOpenSource}><WarningCircle size={17} />{t(currentItems.length ? "otherRemainingWork" : "remainingWork")} <span>{open.length}</span><ArrowRight size={16}/></button></h3><ul>{open.map((item, index) => <li key={index}><span className="check-indicator" />{itemText(item)}</li>)}</ul></div>
            <div><h3><CheckCircle size={17} />{t("completedWork")} <span>{completed.length}</span></h3><ul>{completed.map((item, index) => <li className="completed" key={index}><CheckCircle size={18} weight="fill" />{itemText(item)}</li>)}</ul></div>
          </div>
        </>
      )}
      <div className="info-note"><Info size={19} /><p>{t(currentItems.length ? "todoEvidenceNoteWithCurrent" : "todoEvidenceNote")}</p></div>
    </section>
  );
}

function changeKindLabel(kind: string, t: ReturnType<typeof useI18n>["t"]): string {
  if (kind === "untracked") return t("gitStatusNewFile");
  if (kind === "modified") return t("gitStatusModified");
  if (kind === "added") return t("gitStatusAdded");
  if (kind === "deleted") return t("gitStatusDeleted");
  if (kind === "renamed") return t("gitStatusRenamed");
  if (kind === "copied") return t("gitStatusCopied");
  if (kind === "conflicted") return t("gitStatusConflict");
  return t("gitStatusChanged");
}

function controlStageLabel(stage: ControlLoopStageId, t: ReturnType<typeof useI18n>["t"]): string {
  if (stage === "plan") return t("flowPlan");
  if (stage === "route") return t("flowRoute");
  if (stage === "implement") return t("flowImplement");
  if (stage === "verify") return t("flowVerify");
  return t("flowReport");
}

function evidenceStatusLabel(status: EvidenceStatus, t: ReturnType<typeof useI18n>["t"]): string {
  if (status === "declared") return t("flowDeclared");
  if (status === "observed") return t("flowObserved");
  if (status === "verified") return t("flowVerified");
  if (status === "failed") return t("flowFailed");
  if (status === "stale") return t("flowStale");
  if (status === "unverified") return t("flowUnverified");
  if (status === "not_applicable") return t("flowNotApplicable");
  return t("flowUnobserved");
}

type SituationTone = "declared" | "observed" | "verified" | "unknown";

function SituationRow({
  index,
  icon,
  title,
  copy,
  tone,
  fact,
  source,
  onOpen,
}: {
  index: number;
  icon: ReactNode;
  title: string;
  copy: string;
  tone: SituationTone;
  fact: string;
  source: string;
  onOpen: () => void;
}) {
  const { t } = useI18n();
  return (
    <li className={`situation-row tone-${tone}`}>
      <span className="situation-row-icon" aria-hidden="true">{icon}</span>
      <div className="situation-row-copy">
        <strong><span>{index}</span>{title}</strong>
        <p>{copy}</p>
      </div>
      <span className={`situation-fact fact-${tone}`}><i />{fact}</span>
      <button type="button" className="situation-source" onClick={onOpen} aria-label={t("openSituationSource", { path: source })}>
        <span><code>{source}</code></span>
        <ArrowRight size={15} />
      </button>
    </li>
  );
}

function SituationPanel({ snapshot, work, onSelect }: { snapshot: Snapshot; work: PacketWorkItem[]; onSelect: (id: string) => void }) {
  const { t } = useI18n();
  const packet = snapshot.state.active_packet;
  const currentItems = work.filter((item) => item.current && !item.completed);
  const currentStage = currentControlStage(work, snapshot.protocol.todo_path);
  const packetId = packet?.id ?? t("noActivePacket");
  const phaseLabel = currentStage.status === "declared" && currentStage.id
    ? controlStageLabel(currentStage.id, t)
    : currentStage.status === "ambiguous"
      ? t("currentPhaseAmbiguous")
      : t("currentPhaseUndeclared");
  const currentIndex = currentStage.id ? CONTROL_LOOP.indexOf(currentStage.id) : -1;
  const nextStage = currentIndex >= 0
    ? CONTROL_LOOP[Math.min(currentIndex + 1, CONTROL_LOOP.length - 1)]
    : null;
  const nextPhaseLabel = nextStage ? controlStageLabel(nextStage, t) : t("flowVerify");
  const currentTask = currentItems.map((item) => item.text).join(" · ");
  const statusCopy = currentStage.status === "declared"
    ? t("situationStatusDeclared", { packet: packetId, phase: phaseLabel })
    : currentStage.status === "ambiguous"
      ? t("situationStatusAmbiguous", { packet: packetId })
      : t("situationStatusUndeclared", { packet: packetId });
  const nowCopy = currentStage.status === "declared"
    ? t("situationNowDeclared", { phase: phaseLabel, task: currentTask })
    : t("situationNowUndeclared");
  const reasonCopy = currentStage.status === "declared"
    ? t("situationReasonDeclared", { phase: phaseLabel })
    : currentStage.status === "ambiguous"
      ? t("situationReasonAmbiguous")
      : t("situationReasonUndeclared");
  const nextCopy = currentStage.status === "declared"
    ? t("situationNextDeclared", { phase: nextPhaseLabel })
    : t("situationNextUndeclared");
  const declarationTone: SituationTone = currentStage.status === "declared" ? "declared" : "unknown";
  const declarationFact = currentStage.status === "declared" ? t("factDeclared") : t("factUnknown");
  return (
    <section className={`situation-section phase-${currentStage.status}`} aria-labelledby="situation-heading">
      <div className="situation-heading">
        <p>{t("situationStatus")}</p>
        <h2 id="situation-heading">{statusCopy}</h2>
      </div>
      <ol className="situation-stack">
        <SituationRow index={1} icon={<Clock size={20} />} title={t("situationNow")} copy={nowCopy} tone={declarationTone} fact={declarationFact} source={snapshot.protocol.todo_path} onOpen={() => onSelect("evidence-todo")} />
        <SituationRow index={2} icon={<FlagBanner size={20} />} title={t("situationReason")} copy={reasonCopy} tone={declarationTone} fact={declarationFact} source={snapshot.protocol.todo_path} onOpen={() => onSelect("evidence-todo")} />
        <SituationRow index={3} icon={<WarningCircle size={20} />} title={t("situationCaution")} copy={t("situationCautionCopy")} tone="unknown" fact={t("factUnknown")} source={t("doctorReportJson")} onOpen={() => onSelect("evidence-doctor")} />
        <SituationRow index={4} icon={<ArrowRight size={20} />} title={t("situationNextCheck")} copy={nextCopy} tone="unknown" fact={t("factUnknown")} source={snapshot.state.active_spec?.path ?? snapshot.protocol.state_path} onOpen={() => onSelect(snapshot.state.active_spec ? "evidence-spec" : "evidence-state")} />
      </ol>
      <div className="situation-legend" aria-label={t("situationEvidenceLegend")}>
        <span className="fact-declared"><i />{t("factDeclared")}</span>
        <span className="fact-observed"><i />{t("factObserved")}</span>
        <span className="fact-verified"><i />{t("factVerified")}</span>
        <span className="fact-unknown"><i />{t("factUnknown")}</span>
        <small>{t("situationSourceNote")}</small>
      </div>
    </section>
  );
}

function PacketContext({ snapshot, work, onSelect }: { snapshot: Snapshot; work: PacketWorkItem[]; onSelect: (id: string) => void }) {
  const { t } = useI18n();
  const packet = snapshot.state.active_packet;
  const currentItems = work.filter((item) => item.current && !item.completed);
  return (
    <section className="packet-context-section" aria-labelledby="packet-context-heading">
      <div className="section-heading-row flow-heading-row">
        <div><h2 id="packet-context-heading">{t("currentPacketAndTodo")}</h2><p>{t("currentDeclaredWorkNote")}</p></div>
        <span className="source-chip" title={`${snapshot.protocol.state_path} + ${snapshot.protocol.todo_path}`}>{snapshot.protocol.state_path} + TODO</span>
      </div>
      <div className="packet-context-grid">
        <article className="packet-context-item">
          <Cube size={21} weight="duotone" />
          <div>
            <span>{t("activePacket")}</span>
            <strong>{packet?.id ?? t("noActivePacket")}</strong>
            <p>{packet?.objective ?? t("noPacketObjective")}</p>
          </div>
          <em>{t("packetLifecycle")}: {packet?.status ?? t("notDeclared")}</em>
          <button type="button" onClick={() => onSelect("evidence-state")} aria-label={t("openSituationSource", { path: snapshot.protocol.state_path })}><code>{snapshot.protocol.state_path}</code><ArrowRight size={15} /></button>
        </article>
        <article className="packet-context-item current-todo-context">
          <FlagBanner size={21} weight="duotone" />
          <div>
            <span>{t("currentTodo")}</span>
            {currentItems.length ? (
              <ul>{currentItems.map((item, index) => <li key={index}><strong>{item.phase && !item.phaseConflict ? controlStageLabel(item.phase, t) : t("currentPhaseNeedsCorrection")}</strong><WorkItemDetails item={item} todoPath={snapshot.protocol.todo_path} onOpenSource={() => onSelect(documentSelectionId(snapshot,snapshot.protocol.todo_path))}/></li>)}</ul>
            ) : <p>{t("currentTodoUndeclared")}</p>}
          </div>
          <em>{t("currentTodoCount", { count: currentItems.length })}</em>
          <button type="button" onClick={() => onSelect("evidence-todo")} aria-label={t("openSituationSource", { path: snapshot.protocol.todo_path })}><code>{snapshot.protocol.todo_path}</code><ArrowRight size={15} /></button>
        </article>
      </div>
    </section>
  );
}

function evidenceRoleLabel(roles: string[], t: ReturnType<typeof useI18n>["t"]): string {
  if (roles.includes("active_spec")) return t("evidenceRoleActiveSpec");
  if (roles.includes("todo")) return t("evidenceRoleTodo");
  if (roles.includes("findings")) return t("evidenceRoleFindings");
  if (roles.includes("current_handoff")) return t("evidenceRoleHandoff");
  return t("evidenceRoleRouted");
}

function EvidenceDocuments({ snapshot, documents, onSelect }: { snapshot: Snapshot; documents: LiveDocuments | null; onSelect: (id: string) => void }) {
  const { t } = useI18n();
  const items = documents?.documents ?? [];
  return (
    <section className="evidence-documents-section" aria-labelledby="evidence-documents-heading">
      <div className="section-heading-row flow-heading-row">
        <div><h2 id="evidence-documents-heading">{t("evidenceDocuments")}</h2><p>{t("evidenceDocumentsNote")}</p></div>
        <span className="source-chip">/api/documents</span>
      </div>
      {items.length ? (
        <ul className="evidence-document-grid">
          {items.map((document) => (
            <li key={document.path}>
              <button type="button" onClick={() => onSelect(documentSelectionId(snapshot, document.path))} aria-label={t("openEvidenceDocument", { path: document.path })} title={t("openEvidenceDocument", { path: document.path })}>
                <BookOpenText size={20} />
                <span><strong>{evidenceRoleLabel(document.roles, t)}</strong><code>{document.path}</code></span>
                <em className={document.exists && document.content !== null ? document.truncated ? "preview" : "available" : "missing"}>
                  {document.exists && document.content !== null
                    ? document.truncated ? t("evidenceDocumentPreview") : t("evidenceDocumentAvailable")
                    : t("missing")}
                </em>
                <ArrowRight size={16} />
              </button>
            </li>
          ))}
        </ul>
      ) : <p className="empty-copy">{t("noEvidenceDocuments")}</p>}
    </section>
  );
}

function lensLabel(lens: WorktreeLensId, t: ReturnType<typeof useI18n>["t"]): string {
  if (lens === "control") return t("lensControl");
  if (lens === "implementation") return t("lensImplementation");
  if (lens === "verification") return t("lensVerification");
  if (lens === "evidence") return t("lensEvidence");
  return t("lensDocumentation");
}

function GitScope({ activity }: { activity: DevelopmentActivity | null }) {
  const { t } = useI18n();
  if (!activity) return null;
  const differentRoots = Boolean(
    activity.git_root
    && activity.project_root.replaceAll("\\", "/").toLocaleLowerCase()
      !== activity.git_root.replaceAll("\\", "/").toLocaleLowerCase(),
  );
  return (
    <section className={`git-scope-panel ${differentRoots ? "nested" : "same-root"}`} aria-label={t("gitScope") }>
      <GitBranch size={18} />
      <div><span>{t("projectRoot")}</span><code>{activity.project_root}</code></div>
      <ArrowRight size={14} />
      <div><span>{t("gitRoot")}</span><code>{activity.git_root ?? t("gitUnavailable")}</code></div>
      {differentRoots && activity.git_scope && <small>{t("gitScopePath", { path: activity.git_scope })}</small>}
    </section>
  );
}

function ActivityLists({ activity, limit = 12, lensFilter = null, onClearLensFilter }: { activity: DevelopmentActivity | null; limit?: number; lensFilter?: WorktreeLensId | null; onClearLensFilter?: () => void }) {
  const { locale, t } = useI18n();
  const allFiles = activity?.files ?? [];
  const visibleFiles = lensFilter
    ? allFiles.filter((file) => classifyWorktreePath(file.path) === lensFilter)
    : allFiles;
  return (
    <>
      <GitScope activity={activity} />
      <div className="activity-columns">
        <section className="activity-panel" aria-labelledby="changed-files-heading">
          <div className="activity-panel-heading">
            <h3 id="changed-files-heading"><GitDiff size={19} />{t("observedChanges")}{lensFilter && <small>{lensLabel(lensFilter, t)}</small>}</h3>
            <div className="activity-panel-summary">
              <span aria-label={lensFilter ? t("filteredChangesCount", { filtered: visibleFiles.length, total: allFiles.length }) : undefined}>{lensFilter ? `${visibleFiles.length}/${allFiles.length}` : allFiles.length}</span>
              {lensFilter && onClearLensFilter && <button type="button" onClick={onClearLensFilter} aria-label={t("clearLensFilter")}><X size={14} /><span>{t("allChanges")}</span></button>}
            </div>
          </div>
          {visibleFiles.length ? <ul className="activity-list file-activity-list">{visibleFiles.slice(0, limit).map((file) => <li key={`${file.status}-${file.path}`}><span className={`change-kind kind-${file.kind}`} title={`${t("rawGitStatus")}: ${file.status}`}>{changeKindLabel(file.kind, t)}</span><div><code>{file.path}</code>{file.previous_path && <small>{t("previousPath", { path: file.previous_path })}</small>}</div><TimeLabel value={file.modified_at} /></li>)}</ul> : <p className="activity-empty">{t("noObservedChanges")}</p>}
        </section>
        <section className="activity-panel" aria-labelledby="commit-history-heading">
          <div className="activity-panel-heading"><h3 id="commit-history-heading"><GitCommit size={19} />{t("recentCommits")}</h3><span>{activity?.commits.length ?? 0}</span></div>
          <p className="activity-scope-note">{t("commitsScopedToProject")}</p>
          {activity?.commits.length ? <ol className="activity-list commit-list">{activity.commits.slice(0, limit).map((commit) => <li key={commit.revision}><span className="timeline-dot" /><div><strong>{commit.subject}</strong><code>{commit.short_revision}</code></div><time dateTime={commit.committed_at} title={formatAbsolute(commit.committed_at, locale)}>{formatRelative(commit.committed_at, locale)}</time></li>)}</ol> : <p className="activity-empty">{t("noRecentCommits")}</p>}
        </section>
        <section className="activity-panel" aria-labelledby="handoff-history-heading">
          <div className="activity-panel-heading"><h3 id="handoff-history-heading"><Stack size={19} />{t("handoffHistory")}</h3><span>{activity?.handoffs.length ?? 0}</span></div>
          {activity?.handoffs.length ? <ol className="activity-list handoff-list">{activity.handoffs.slice(0, limit).map((handoff) => <li key={handoff.path}><FileText size={18} /><div><strong>{handoff.title}</strong><code>{handoff.path}</code>{handoff.summary && <small>{handoff.summary}</small>}</div><span className="handoff-time">{handoff.current && <em>{t("currentRecord")}</em>}<TimeLabel value={handoff.modified_at} /></span></li>)}</ol> : <p className="activity-empty">{t("noHandoffHistory")}</p>}
        </section>
      </div>
    </>
  );
}

export function PacketEvidencePanel({ snapshot, activity, work, onSelect }: { snapshot: Snapshot; documents: LiveDocuments | null; activity: DevelopmentActivity | null; work: PacketWorkItem[]; onSelect: (id:string) => void }) {
  const { locale, t } = useI18n();
  return (
    <section className="overview-section packet-evidence-section" aria-label={t("packetTodo")}>
      <WorkChecklist work={work} todoPath={snapshot.protocol.todo_path} onOpenSource={() => onSelect(documentSelectionId(snapshot,snapshot.protocol.todo_path))}/>
      <div className="observed-signal-row">
        <div><span className={`signal-dot ${activity?.worktree_status ?? "unavailable"}`} /><span>{activity?.worktree_status === "changed" ? t("worktreeChanged") : activity?.worktree_status === "clean" ? t("worktreeClean") : t("gitUnavailable")}</span></div>
        {activity && <small>{t("activityFreshness", { time: formatRelative(activity.scanned_at, locale), duration: activity.duration_ms })}</small>}
      </div>
      <p className="evidence-caveat">{t("observedWhileActive")}</p>
      <ActivityLists activity={activity} limit={7} />
      <p className="timestamp-note"><Clock size={16} />{t("timestampBasis")}</p>
    </section>
  );
}

export function DevelopmentFlowView({ snapshot, documents, activity, work, onSelect }: { snapshot: Snapshot; documents: LiveDocuments | null; activity: DevelopmentActivity | null; work: PacketWorkItem[]; onSelect: (id: string) => void }) {
  const { locale, t } = useI18n();
  const [selectedLens, setSelectedLens] = useState<WorktreeLensId | null>(null);
  const [planTarget, setPlanTarget] = useState<string | null>(null);
  const planId = useId();
  const planKey = JSON.stringify([snapshot.project.root,snapshot.state.active_packet?.id]);
  const planOpen = planTarget === planKey;
  const detailCopy = workDetailCopy[locale];
  const stages = controlLoopSignals(snapshot, documents, activity);
  const currentStage = currentControlStage(work, snapshot.protocol.todo_path);
  const branches = conditionalBranchSignals(snapshot, documents, activity);
  const lenses = worktreeLensSignals(activity);
  const ownerGate = branches.find((branch) => branch.id === "owner_gate")!;
  const handoff = branches.find((branch) => branch.id === "handoff")!;
  return (
    <div className="context-view development-view">
      <header className="development-header">
        <div><h1>{t("officialControlLoop")}</h1><span>{t("readOnlyParenthetical")}</span><p>{t("controlLoopEvidenceNote")}</p></div>
        <div className={`live-signal signal-${activity?.worktree_status ?? "unavailable"}`}><span /><strong>{activity?.worktree_status === "changed" ? t("worktreeChanged") : activity?.worktree_status === "clean" ? t("worktreeClean") : t("gitUnavailable")}</strong>{activity && <small>{t("activityFreshness", { time: formatRelative(activity.scanned_at, locale), duration: activity.duration_ms })}</small>}</div>
      </header>
      {activity?.error && <div className="development-error"><WarningCircle size={19} /><span><strong>{activity.error.code}</strong>{activity.error.message}</span></div>}

      <section className="official-flow-section" aria-labelledby="official-flow-heading">
        <h2 className="sr-only" id="official-flow-heading">{t("officialControlLoop")}</h2>
        <div className="flow-orientation-scroll">
          <ol className="explainable-flow-rail" aria-label={t("officialControlLoop")}>
          {stages.map((stage, index) => (
            <li className={`flow-step evidence-${stage.status} ${currentStage.id === stage.id ? "is-current" : ""}`} key={stage.id} aria-current={currentStage.id === stage.id ? "step" : undefined}>
              <span className="flow-step-marker">{index + 1}</span>
              {stage.id === 'plan' ? <button type="button" className="plan-detail-trigger" aria-label={planOpen ? detailCopy.closePlan : detailCopy.openPlan} aria-expanded={planOpen} aria-controls={planId} onClick={() => setPlanTarget(planOpen ? null : planKey)}><strong>{controlStageLabel(stage.id,t)}</strong><ArrowRight size={13} aria-hidden="true"/></button> : <strong>{controlStageLabel(stage.id, t)}</strong>}
              <em>{evidenceStatusLabel(stage.status, t)}</em>
              {currentStage.id === stage.id && <span className="sr-only">{t("currentStageBadge")}</span>}
            </li>
          ))}
          </ol>
        </div>
        <div className="orientation-note"><Info size={16} /><span>{t("officialControlLoopNote")}</span><code title={snapshot.protocol.adapter_id}>{snapshot.protocol.engine_name}</code></div>
        <div id={planId}>{planOpen && <PlanDetails snapshot={snapshot} documents={documents} work={work} onSelect={onSelect}/>}</div>
      </section>

      <InteractionPanel key={snapshot.project.identity} snapshot={snapshot} documents={documents} onSelect={onSelect} />
      <SituationPanel snapshot={snapshot} work={work} onSelect={onSelect} />
      <PacketContext snapshot={snapshot} work={work} onSelect={onSelect} />
      <EvidenceDocuments snapshot={snapshot} documents={documents} onSelect={onSelect} />

      <section className="conditional-flow" aria-labelledby="conditional-flow-heading">
        <div className="section-heading-row flow-heading-row"><div><h2 id="conditional-flow-heading">{t("conditionalBranches")}</h2><p>{t("conditionalBranchesNote")}</p></div></div>
        <div className="conditional-branch-grid">
          <article className={`conditional-branch evidence-${ownerGate.status}`}>
            <Shield size={22} />
            <div><div className="branch-title"><strong>{t("ownerGateBranch")}</strong><span>{evidenceStatusLabel(ownerGate.status, t)}</span></div><p>{snapshot.state.owner_gates.length ? t("gateDeclaredApprovalUnobserved") : t("flowNotApplicable")}</p>{snapshot.state.owner_gates.length > 0 && <ul>{snapshot.state.owner_gates.map((gate) => <li key={gate}><code>{gate}</code></li>)}</ul>}<small><Lock size={14} />{t("inspectorReadOnlyProtected")}</small></div>
          </article>
          <article className={`conditional-branch evidence-${handoff.status}`}>
            <Stack size={22} />
            <div><div className="branch-title"><strong>{t("handoffBranch")}</strong><span>{evidenceStatusLabel(handoff.status, t)}</span></div><p>{snapshot.state.current_handoff?.declared ? snapshot.state.current_handoff.path ?? t("flowUnobserved") : t("handoffNotApplicable")}</p><small>{t("handoffConditionalNote")}</small></div>
          </article>
        </div>
      </section>

      <section className="worktree-lens-section" aria-labelledby="worktree-lens-heading">
        <div className="section-heading-row flow-heading-row"><div><h2 id="worktree-lens-heading">{t("worktreeEvidenceLens")}</h2><p>{t("worktreeEvidenceLensNote")}</p></div></div>
        <div className="worktree-lens-controls">
          {lenses.map((lens) => <button type="button" key={lens.id} className={selectedLens === lens.id ? "active" : ""} aria-pressed={selectedLens === lens.id} aria-label={t("filterLensChanges", { lens: lensLabel(lens.id, t), count: lens.changedCount })} onClick={() => setSelectedLens((value) => value === lens.id ? null : lens.id)}><span>{lensLabel(lens.id, t)}</span><strong>{lens.changedCount}</strong></button>)}
        </div>
        <div className={`flow-filter-status ${selectedLens ? "active" : ""}`}><FunnelSimple size={16} /><span>{selectedLens ? t("lensFilterActive", { lens: lensLabel(selectedLens, t) }) : t("lensFilterHint")}</span></div>
      </section>

      <section className="development-work-section"><WorkChecklist work={work} todoPath={snapshot.protocol.todo_path} showCurrent={false} onOpenSource={() => onSelect(documentSelectionId(snapshot,snapshot.protocol.todo_path))}/></section>
      <ActivityLists activity={activity} limit={20} lensFilter={selectedLens} onClearLensFilter={() => setSelectedLens(null)} />
      <div className="info-note development-note"><Info size={20} /><p>{t("observedWhileActive")} {t("timestampBasis")}</p></div>
    </div>
  );
}
