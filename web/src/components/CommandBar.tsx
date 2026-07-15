import { useState } from "react";
import {
  ArrowsClockwise,
  BracketsCurly,
  Copy,
  DotsThreeVertical,
  Folder,
  FolderOpen,
  HandPalm,
  Moon,
  Sun,
  Timer,
  Translate as TranslateIcon,
} from "@phosphor-icons/react";
import { type Locale, useI18n } from "../i18n";
import type { Theme } from "../theme";
import type { RescanMode, Snapshot } from "../types";

interface Props {
  snapshot: Snapshot;
  busy: boolean;
  onRescan: () => void;
  onReveal: () => void;
  onCopy: () => void;
  onOpenProject: () => void;
  onCopySnapshot: () => void;
  onToggleRepository: () => void;
  onToggleInspector: () => void;
  theme: Theme;
  onToggleTheme: () => void;
  rescanMode: RescanMode;
  autoSeconds: number;
  onRescanModeChange: (mode: RescanMode) => void;
}

export function CommandBar({
  snapshot,
  busy,
  onRescan,
  onReveal,
  onCopy,
  onOpenProject,
  onCopySnapshot,
  onToggleRepository,
  onToggleInspector,
  theme,
  onToggleTheme,
  rescanMode,
  autoSeconds,
  onRescanModeChange,
}: Props) {
  const { locale, setLocale, t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <header className="command-bar">
      <button className="mobile-pane-button repo-toggle" onClick={onToggleRepository} aria-label={t("openRepositoryControls")}>
        <Folder size={19} />
      </button>
      <div className="brand" aria-label="SDAD Inspector">
        <span className="brand-mark"><BracketsCurly size={17} weight="bold" /></span>
        <span className="brand-name">SDAD Inspector</span>
      </div>
      <span className="command-divider" />
      <button className="project-path" onClick={onOpenProject} title={t("switchProject")}>
        <Folder size={18} />
        <span>{snapshot.project.root}</span>
      </button>
      <span className="command-divider engine-divider" />
      <div className="engine-label">
        <span>{t("engine")}</span>
        <strong>SDAD {snapshot.engine.doctor_version}</strong>
      </div>
      <div className="command-actions">
        <div className="scan-mode-control" role="group" aria-label={t("autoRescan")}>
          <button className={rescanMode === "manual" ? "active" : ""} onClick={() => onRescanModeChange("manual")} aria-label={t("manual")} aria-pressed={rescanMode === "manual"}><HandPalm size={15} /><span>{t("manual")}</span></button>
          <button className={rescanMode === "auto" ? "active" : ""} onClick={() => onRescanModeChange("auto")} aria-label={t("auto15Seconds")} aria-pressed={rescanMode === "auto"}><Timer size={15} /><span>{t("auto15Seconds")}</span></button>
          {rescanMode === "auto" && <span title={t("nextScanIn", { seconds: autoSeconds })}>{autoSeconds}s</span>}
        </div>
        <button className="command-action primary-command" onClick={onRescan} disabled={busy} aria-label={busy ? t("scanning") : t("rescan")}>
          <ArrowsClockwise className={busy ? "spin" : ""} size={19} />
          <span>{busy ? t("scanning") : t("rescan")}</span>
        </button>
        <span className="command-divider" />
        <button className="command-action" onClick={onReveal}>
          <FolderOpen size={19} />
          <span>{t("revealInFolder")}</span>
        </button>
        <button className="command-action" onClick={onCopy}>
          <Copy size={18} />
          <span>{t("copyPath")}</span>
        </button>
        <label className="language-select" title={t("language")}>
          <TranslateIcon size={17} />
          <span className="sr-only">{t("language")}</span>
          <select
            aria-label={t("language")}
            value={locale}
            onChange={(event) => setLocale(event.target.value as Locale)}
          >
            <option value="ko">{t("korean")}</option>
            <option value="en">{t("english")}</option>
          </select>
        </label>
        <button
          className="icon-button theme-toggle"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? t("useLightTheme") : t("useDarkTheme")}
          title={theme === "dark" ? t("useLightTheme") : t("useDarkTheme")}
        >
          {theme === "dark" ? <Sun size={19} /> : <Moon size={19} />}
        </button>
        <div className="overflow-wrap">
          <button
            className="icon-button"
            aria-label={t("moreActions")}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((value) => !value)}
          >
            <DotsThreeVertical size={20} weight="bold" />
          </button>
          {menuOpen && (
            <div className="overflow-menu" role="menu">
              <button role="menuitem" onClick={() => { setMenuOpen(false); onOpenProject(); }}>
                <FolderOpen size={17} /> {t("openProject")}
              </button>
              <button role="menuitem" onClick={() => { setMenuOpen(false); onCopySnapshot(); }}>
                <Copy size={17} /> {t("copySnapshotJson")}
              </button>
            </div>
          )}
        </div>
      </div>
      <button className="mobile-pane-button inspector-toggle" onClick={onToggleInspector} aria-label={t("openInspectorPane")}>
        <BracketsCurly size={19} />
      </button>
    </header>
  );
}
