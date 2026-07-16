import { Lock } from "@phosphor-icons/react";
import { useI18n } from "../i18n";
import type { Snapshot } from "../types";

const REPOSITORY_URL = "https://github.com/LiveTrack-X/sdad-inspector";

export function StatusBar({ snapshot, onOpenRepository }: { snapshot: Snapshot; onOpenRepository: () => void }) {
  const { t } = useI18n();
  return (
    <footer className="status-bar" aria-label={t("inspectionProvenance")}>
      <a className="creator-link" href={REPOSITORY_URL} target="_blank" rel="noreferrer" onClick={(event) => { event.preventDefault(); onOpenRepository(); }} aria-label={t("openProductRepository")}>{t("createdByLiveTrack")}</a>
      <span><em>{t("doctor")}</em><strong>{snapshot.contracts.doctor_version}</strong></span>
      <span><em>{t("reportSchema")}</em><strong>{snapshot.contracts.report_schema_version}</strong></span>
      <span><em>{t("stateSchema")}</em><strong>{snapshot.contracts.state_schema_version ?? "—"}</strong></span>
      <span><em>{t("snapshotSchemaLabel")}</em><strong>{snapshot.contracts.snapshot_schema_version}</strong></span>
      <span><em>{t("doctorExitCode")}</em><strong>{snapshot.doctor.exit_code}</strong></span>
      <span className="status-time"><em>{t("inspectedAt")}</em><strong>{snapshot.inspected_at}</strong></span>
      <span className="read-only-status"><Lock size={16} /><strong>{t("readOnly")}</strong></span>
    </footer>
  );
}
