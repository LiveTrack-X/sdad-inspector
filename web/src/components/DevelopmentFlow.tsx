import { useState } from "react";
import { CheckCircle, Clock, FileText, FunnelSimple, GitCommit, GitDiff, Info, Stack, WarningCircle, X } from "@phosphor-icons/react";
import { classifyDevelopmentPath, developmentStageSignals, type DevelopmentStageId, type DevelopmentStageStatus } from "../developmentStages";
import { useI18n } from "../i18n";
import type { PacketWorkItem } from "../packetWork";
import { formatAbsolute, formatRelative } from "../time";
import type { DevelopmentActivity, LiveDocuments, Snapshot } from "../types";

function TimeLabel({ value }: { value: string | null }) {
  const { locale } = useI18n();
  if (!value) return <span className="time-label">—</span>;
  return <time className="time-label" dateTime={value} title={formatAbsolute(value, locale)}>{formatRelative(value, locale)}</time>;
}

function WorkChecklist({ work }: { work: PacketWorkItem[] }) {
  const { t } = useI18n();
  const open = work.filter((item) => !item.completed);
  const completed = work.filter((item) => item.completed);
  const showSections = new Set(work.map((item) => item.section)).size > 1;
  const itemText = (item: PacketWorkItem) => <div><p>{item.text}</p>{showSections && <small className="todo-source-section">{t("todoSourceSection", { section: item.section })}</small>}</div>;
  return (
    <section className="packet-work" aria-labelledby="packet-work-heading">
      <div className="section-heading-row">
        <h2 id="packet-work-heading">{t("packetTodo")}</h2>
        <span className="source-chip">docs/TODO-Open-Items.md</span>
      </div>
      {!work.length ? <p className="empty-copy">{t("noPacketTaggedWork")}</p> : (
        <div className="work-columns">
          <div><h3><WarningCircle size={17} />{t("remainingWork")} <span>{open.length}</span></h3><ul>{open.map((item, index) => <li key={index}><span className="check-indicator" />{itemText(item)}</li>)}</ul></div>
          <div><h3><CheckCircle size={17} />{t("completedWork")} <span>{completed.length}</span></h3><ul>{completed.map((item, index) => <li className="completed" key={index}><CheckCircle size={18} weight="fill" />{itemText(item)}</li>)}</ul></div>
        </div>
      )}
      <div className="info-note"><Info size={19} /><p>{t("todoEvidenceNote")}</p></div>
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

function stageLabel(stage: DevelopmentStageId, t: ReturnType<typeof useI18n>["t"]): string {
  if (stage === "scope") return t("flowScope");
  if (stage === "build") return t("flowBuild");
  if (stage === "verify") return t("flowVerify");
  if (stage === "evidence") return t("flowEvidence");
  return t("flowDocsHandoff");
}

function stageStatusLabel(status: DevelopmentStageStatus, t: ReturnType<typeof useI18n>["t"]): string {
  if (status === "current") return t("flowCurrentObservation");
  if (status === "observed") return t("flowObserved");
  if (status === "declared") return t("flowDeclared");
  return t("flowNoSignal");
}

function ActivityLists({ activity, limit = 12, stageFilter = null, onClearStageFilter }: { activity: DevelopmentActivity | null; limit?: number; stageFilter?: DevelopmentStageId | null; onClearStageFilter?: () => void }) {
  const { locale, t } = useI18n();
  const allFiles = activity?.files ?? [];
  const visibleFiles = stageFilter
    ? allFiles.filter((file) => classifyDevelopmentPath(file.path) === stageFilter)
    : allFiles;
  return (
    <div className="activity-columns">
      <section className="activity-panel" aria-labelledby="changed-files-heading">
        <div className="activity-panel-heading">
          <h3 id="changed-files-heading"><GitDiff size={19} />{t("observedChanges")}{stageFilter && <small>{stageLabel(stageFilter, t)}</small>}</h3>
          <div className="activity-panel-summary">
            <span aria-label={stageFilter ? t("filteredChangesCount", { filtered: visibleFiles.length, total: allFiles.length }) : undefined}>{stageFilter ? `${visibleFiles.length}/${allFiles.length}` : allFiles.length}</span>
            {stageFilter && onClearStageFilter && <button type="button" onClick={onClearStageFilter} aria-label={t("clearStageFilter")}><X size={14} /><span>{t("allChanges")}</span></button>}
          </div>
        </div>
        {visibleFiles.length ? <ul className="activity-list file-activity-list">{visibleFiles.slice(0, limit).map((file) => <li key={`${file.status}-${file.path}`}><span className={`change-kind kind-${file.kind}`} title={`${t("rawGitStatus")}: ${file.status}`}>{changeKindLabel(file.kind, t)}</span><div><code>{file.path}</code>{file.previous_path && <small>{t("previousPath", { path: file.previous_path })}</small>}</div><TimeLabel value={file.modified_at} /></li>)}</ul> : <p className="activity-empty">{t("noObservedChanges")}</p>}
      </section>
      <section className="activity-panel" aria-labelledby="commit-history-heading">
        <div className="activity-panel-heading"><h3 id="commit-history-heading"><GitCommit size={19} />{t("recentCommits")}</h3><span>{activity?.commits.length ?? 0}</span></div>
        {activity?.commits.length ? <ol className="activity-list commit-list">{activity.commits.slice(0, limit).map((commit) => <li key={commit.revision}><span className="timeline-dot" /><div><strong>{commit.subject}</strong><code>{commit.short_revision}</code></div><time dateTime={commit.committed_at} title={formatAbsolute(commit.committed_at, locale)}>{formatRelative(commit.committed_at, locale)}</time></li>)}</ol> : <p className="activity-empty">{t("noRecentCommits")}</p>}
      </section>
      <section className="activity-panel" aria-labelledby="handoff-history-heading">
        <div className="activity-panel-heading"><h3 id="handoff-history-heading"><Stack size={19} />{t("handoffHistory")}</h3><span>{activity?.handoffs.length ?? 0}</span></div>
        {activity?.handoffs.length ? <ol className="activity-list handoff-list">{activity.handoffs.slice(0, limit).map((handoff) => <li key={handoff.path}><FileText size={18} /><div><strong>{handoff.title}</strong><code>{handoff.path}</code>{handoff.summary && <small>{handoff.summary}</small>}</div><span className="handoff-time">{handoff.current && <em>{t("currentRecord")}</em>}<TimeLabel value={handoff.modified_at} /></span></li>)}</ol> : <p className="activity-empty">{t("noHandoffHistory")}</p>}
      </section>
    </div>
  );
}

export function PacketEvidencePanel({ snapshot, documents, activity, work }: { snapshot: Snapshot; documents: LiveDocuments | null; activity: DevelopmentActivity | null; work: PacketWorkItem[] }) {
  const { locale, t } = useI18n();
  return (
    <section className="overview-section packet-evidence-section" aria-label={t("packetTodo")}>
      <WorkChecklist work={work} />
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

export function DevelopmentFlowView({ snapshot, documents, activity, work }: { snapshot: Snapshot; documents: LiveDocuments | null; activity: DevelopmentActivity | null; work: PacketWorkItem[] }) {
  const { locale, t } = useI18n();
  const [selectedStage, setSelectedStage] = useState<DevelopmentStageId | null>(null);
  const open = work.filter((item) => !item.completed).length;
  const completed = work.filter((item) => item.completed).length;
  const stages = developmentStageSignals(snapshot, activity);
  const current = stages.find((stage) => stage.status === "current");
  return (
    <div className="context-view development-view">
      <header className="development-header">
        <div><p className="section-kicker">{t("liveRepositorySignal")}</p><h1>{t("developmentFlow")}</h1><p>{t("timestampBasis")}</p></div>
        <div className={`live-signal signal-${activity?.worktree_status ?? "unavailable"}`}><span /><strong>{activity?.worktree_status === "changed" ? t("worktreeChanged") : activity?.worktree_status === "clean" ? t("worktreeClean") : t("gitUnavailable")}</strong>{activity && <small>{t("activityFreshness", { time: formatRelative(activity.scanned_at, locale), duration: activity.duration_ms })}</small>}</div>
      </header>
      {activity?.error && <div className="development-error"><WarningCircle size={19} /><span><strong>{activity.error.code}</strong>{activity.error.message}</span></div>}
      <div className="flow-current-basis"><Info size={18} /><div><strong>{current ? t("flowCurrentFrom", { stage: stageLabel(current.id, t) }) : t("flowCurrentUnavailable")}</strong><span>{current?.currentBasis ?? t("flowCurrentBasisNote")}</span></div></div>
      <section className="flow-rail" aria-label={t("developmentFlow")}>
        {stages.map((stage, index) => <button type="button" className={`flow-stage stage-${stage.status} ${selectedStage === stage.id ? "filter-active" : ""}`} key={stage.id} aria-current={stage.status === "current" ? "step" : undefined} aria-pressed={selectedStage === stage.id} aria-label={t("filterStageChanges", { stage: stageLabel(stage.id, t), count: stage.changedCount })} onClick={() => setSelectedStage((value) => value === stage.id ? null : stage.id)}><div className="flow-stage-top"><span>{index + 1}</span><em>{stageStatusLabel(stage.status, t)}</em></div><strong>{stageLabel(stage.id, t)}</strong><small>{stage.id === "scope" ? `${snapshot.state.active_packet?.id ?? t("notDeclared")} · ${open} ${t("remainingWork")} · ${completed} ${t("completedWork")}` : stage.id === "verify" ? `${t("pathsChanged", { count: stage.changedCount })} · ${snapshot.state.validation.length} ${t("declaredCommands")} · ${t("notExecutedShort")}` : stage.id === "docs" ? `${t("pathsChanged", { count: stage.changedCount })} · ${t("handoffsCount", { count: activity?.handoffs.length ?? 0 })}` : t("pathsChanged", { count: stage.changedCount })}</small>{stage.latestPath && <code>{stage.latestPath}</code>}</button>)}
      </section>
      <div className={`flow-filter-status ${selectedStage ? "active" : ""}`}><FunnelSimple size={16} /><span>{selectedStage ? t("stageFilterActive", { stage: stageLabel(selectedStage, t) }) : t("stageFilterHint")}</span></div>
      <section className="development-work-section"><WorkChecklist work={work} /></section>
      <ActivityLists activity={activity} limit={20} stageFilter={selectedStage} onClearStageFilter={() => setSelectedStage(null)} />
      <div className="info-note development-note"><Info size={20} /><p>{t("observedWhileActive")} {t("timestampBasis")}</p></div>
    </div>
  );
}
