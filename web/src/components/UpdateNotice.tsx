import { ArrowsClockwise, CheckCircle, DownloadSimple, WarningCircle } from "@phosphor-icons/react";
import { useI18n } from "../i18n";
import type { ProductUpdateStatus } from "../types";

interface Props {
  status: ProductUpdateStatus | null;
  countdown: number | null;
  inspectionBusy: boolean;
  postponed: boolean;
  onApply: () => void;
  onPostpone: () => void;
  onRetry: () => void;
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 MB";
  return `${(value / (1024 * 1024)).toFixed(value >= 100 * 1024 * 1024 ? 0 : 1)} MB`;
}

export function UpdateNotice({ status, countdown, inspectionBusy, postponed, onApply, onPostpone, onRetry }: Props) {
  const { t } = useI18n();
  if (!status?.supported || ["idle", "unsupported", "up_to_date"].includes(status.state)) return null;

  if (status.state === "checking") {
    return <aside className="update-notice neutral" role="status"><ArrowsClockwise className="spin" size={19} /><span><strong>{t("updateChecking")}</strong><small>{t("updateCheckingDetail")}</small></span></aside>;
  }

  if (status.state === "downloading") {
    const maximum = Math.max(1, status.total_bytes);
    return (
      <aside className="update-notice neutral" role="status">
        <DownloadSimple size={20} />
        <span>
          <strong>{t("updateDownloading", { version: status.available_version ?? "" })}</strong>
          <small>{t("updateDownloadProgress", { downloaded: formatBytes(status.downloaded_bytes), total: formatBytes(status.total_bytes) })}</small>
          <progress value={Math.min(status.downloaded_bytes, maximum)} max={maximum} aria-label={t("updateDownloadProgressLabel")} />
        </span>
      </aside>
    );
  }

  if (status.state === "ready") {
    const detail = postponed
      ? t("updatePostponedDetail")
      : inspectionBusy
        ? t("updateWaitingForInspection")
        : t("updateRestartCountdown", { seconds: countdown ?? 0 });
    return (
      <aside className="update-notice ready" role="status">
        <CheckCircle size={20} weight="fill" />
        <span><strong>{t("updateReady", { version: status.available_version ?? "" })}</strong><small>{detail}</small></span>
        <div className="update-notice-actions">
          <button className="primary" onClick={onApply} disabled={inspectionBusy}>{t("restartAndUpdateNow")}</button>
          {!postponed && <button onClick={onPostpone}>{t("updateLater")}</button>}
        </div>
      </aside>
    );
  }

  if (status.state === "applying") {
    return <aside className="update-notice ready" role="status"><ArrowsClockwise className="spin" size={19} /><span><strong>{t("updateApplying")}</strong><small>{t("updateApplyingDetail")}</small></span></aside>;
  }

  if (status.state === "updated") {
    return <aside className="update-notice success" role="status"><CheckCircle size={20} weight="fill" /><span><strong>{t("updateCompleted")}</strong><small>{t("updateCompletedDetail", { version: status.current_version })}</small></span></aside>;
  }

  return (
    <aside className="update-notice error" role="alert">
      <WarningCircle size={20} />
      <span><strong>{t("updateFailed")}</strong><small>{status.error ?? t("updateFailedDetail")}</small></span>
      <div className="update-notice-actions"><button onClick={onRetry}>{t("tryUpdateAgain")}</button></div>
    </aside>
  );
}
