import { Check, FileText, Lock, SpinnerGap } from "@phosphor-icons/react";
import { type Translate, useI18n } from "../i18n";
import type { InspectionProgress as Progress, InspectionStage } from "../types";

const STAGES: InspectionStage[] = ["prepare", "doctor", "controls", "integrity", "report"];

function stageLabel(stage: InspectionStage, t: Translate): string {
  if (stage === "prepare") return t("scanStagePrepare");
  if (stage === "doctor") return t("scanStageDoctor");
  if (stage === "controls") return t("scanStageControls");
  if (stage === "integrity") return t("scanStageIntegrity");
  return t("scanStageReport");
}

function eventLabel(event: string, t: Translate): string {
  if (event === "inspection_started") return t("progressInspectionStarted");
  if (event === "project_boundary_ready") return t("progressProjectReady");
  if (event === "doctor_started") return t("progressDoctorStarted");
  if (event === "doctor_completed") return t("progressDoctorCompleted");
  if (event === "control_source_read") return t("progressControlRead");
  if (event === "integrity_check_started") return t("progressIntegrityStarted");
  if (event === "snapshot_assembly_started") return t("progressReportStarted");
  if (event === "snapshot_serialized") return t("progressSnapshotReady");
  if (event === "inspection_completed") return t("progressInspectionCompleted");
  if (event === "inspection_failed") return t("progressInspectionFailed");
  return event.replaceAll("_", " ");
}

interface Props {
  active: boolean;
  progress: Progress | null;
}

export function InspectionProgress({ active, progress }: Props) {
  const { t } = useI18n();
  if (!active) return null;

  const completed = progress?.status === "completed";
  const currentIndex = progress?.stage_index ?? 0;
  const recent = progress?.recent.slice(-4).reverse() ?? [];
  return (
    <section className={`scan-progress ${completed ? "completed" : ""}`} aria-live="polite" aria-busy={!completed}>
      <div className="scan-progress-heading">
        <span className="scan-spinner">{completed ? <Check size={18} weight="bold" /> : <SpinnerGap className="spin" size={19} />}</span>
        <div>
          <p>{t("liveInspection")}</p>
          <h2>{completed ? t("inspectionComplete") : t("inspectionInProgress")}</h2>
        </div>
        <span className="scan-observed">{t("serviceObserved")}</span>
      </div>

      <ol className="scan-stages" aria-label={t("inspectionStages")}>
        {STAGES.map((stage, index) => {
          const number = index + 1;
          const state = number < currentIndex ? "complete" : number === currentIndex ? "current" : "pending";
          return (
            <li className={state} key={stage} aria-current={state === "current" ? "step" : undefined}>
              <span className="scan-stage-marker">{state === "complete" ? <Check size={14} weight="bold" /> : number}</span>
              <span>{stageLabel(stage, t)}</span>
            </li>
          );
        })}
      </ol>

      <div className="scan-live-grid">
        <div className="scan-live-fact">
          <span>{t("liveStage")}</span>
          <strong>{progress ? stageLabel(progress.stage, t) : t("awaitingObservedStage")}</strong>
        </div>
        <div className="scan-live-fact current-source">
          <span>{t("currentSource")}</span>
          <code>{progress?.current_source ?? t("waitingForService")}</code>
        </div>
      </div>

      {recent.length > 0 && (
        <div className="scan-recent">
          <h3>{t("recentWork")}</h3>
          <ul>
            {recent.map((item, index) => (
              <li key={`${item.at}-${item.source}-${index}`}>
                <FileText size={15} />
                <code>{item.source}</code>
                <span>{eventLabel(item.event, t)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="scan-progress-note"><Lock size={14} /> {t("observedProgressNote")}</p>
    </section>
  );
}
