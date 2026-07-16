import { type FormEvent, useEffect, useRef, useState } from "react";
import { ClipboardText, ClockCounterClockwise, FolderOpen, FolderSimplePlus, Trash, X } from "@phosphor-icons/react";
import { useI18n } from "../i18n";
import type { RecentProject } from "../types";

interface Props {
  currentPath: string | null;
  open: boolean;
  required?: boolean;
  busy: boolean;
  error?: string | null;
  recentProjects: RecentProject[];
  onClose: () => void;
  onSubmit: (path: string) => void;
  onBrowse: (initialPath: string) => Promise<string | null>;
  onPaste: () => Promise<string>;
  onClearRecent: () => void;
}

export function ProjectDialog({ currentPath, open, required = false, busy, error, recentProjects, onClose, onSubmit, onBrowse, onPaste, onClearRecent }: Props) {
  const { t } = useI18n();
  const [path, setPath] = useState(currentPath ?? "");
  const [interactionBusy, setInteractionBusy] = useState(false);
  const [interactionError, setInteractionError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (open) {
      setPath(currentPath ?? ""); setInteractionError(null);
      window.setTimeout(() => inputRef.current?.select(), 0);
    }
  }, [open, currentPath]);
  if (!open) return null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (path.trim()) onSubmit(path.trim());
  }

  async function browse() {
    setInteractionBusy(true); setInteractionError(null);
    try {
      const selected = await onBrowse(path.trim() || currentPath || "");
      if (selected) { setPath(selected); onSubmit(selected); }
    } catch (reason) {
      setInteractionError(reason instanceof Error ? reason.message : t("folderPickerFailed"));
    } finally { setInteractionBusy(false); }
  }

  async function paste() {
    setInteractionBusy(true); setInteractionError(null);
    try {
      const pasted = await onPaste(); setPath(pasted); inputRef.current?.focus();
    } catch (reason) {
      setInteractionError(reason instanceof Error ? reason.message : t("clipboardPasteFailed"));
    } finally { setInteractionBusy(false); }
  }

  const disabled = busy || interactionBusy;
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (!required && event.target === event.currentTarget) onClose(); }}>
      <section className="project-dialog" role="dialog" aria-modal="true" aria-labelledby="project-dialog-title">
        <div className="dialog-heading"><FolderOpen size={23} /><h2 id="project-dialog-title">{t("openSdadProject")}</h2>{!required && <button onClick={onClose} aria-label={t("close")}><X size={20} /></button>}</div>
        <p>{t("openProjectHelp")}</p>
        <div className="project-shortcuts">
          {currentPath && <section aria-labelledby="current-project-heading">
            <h3 id="current-project-heading">{t("currentProject")}</h3>
            <button className="project-shortcut current" onClick={() => onSubmit(currentPath)} disabled={disabled}>
              <FolderOpen size={19} /><span><strong>{currentPath.split(/[\\/]/).filter(Boolean).at(-1) ?? currentPath}</strong><code>{currentPath}</code></span>
            </button>
          </section>}
          <section aria-labelledby="recent-projects-heading">
            <div className="shortcut-heading"><h3 id="recent-projects-heading">{t("recentProjects")}</h3><button className="clear-history" onClick={onClearRecent} disabled={disabled || recentProjects.length === 0}><Trash size={16} />{t("clearHistory")}</button></div>
            {recentProjects.length ? <ul className="recent-project-list">{recentProjects.map((project) => <li key={project.path}><button onClick={() => onSubmit(project.path)} disabled={disabled}><ClockCounterClockwise size={18} /><span><strong>{project.name}</strong><code>{project.path}</code></span></button></li>)}</ul> : <p className="recent-empty">{t("noRecentProjects")}</p>}
          </section>
        </div>
        <form onSubmit={submit}>
          <label htmlFor="project-root">{t("projectRoot")}</label>
          <div className="path-entry-row">
            <input ref={inputRef} id="project-root" value={path} onChange={(event) => setPath(event.target.value)} onPaste={() => setInteractionError(null)} spellCheck={false} autoComplete="off" />
            <button type="button" className="entry-action" onClick={() => void paste()} disabled={disabled} title={t("pastePath")}><ClipboardText size={19} /><span>{t("paste")}</span></button>
            <button type="button" className="entry-action browse-action" onClick={() => void browse()} disabled={disabled} title={t("chooseFolder")}><FolderSimplePlus size={19} /><span>{t("browse")}</span></button>
          </div>
          {(interactionError || error) && <p className="dialog-error" role="alert">{interactionError || error}</p>}
          <div className="dialog-actions">{!required && <button type="button" onClick={onClose}>{t("cancel")}</button>}<button className="primary" disabled={disabled || !path.trim()}>{busy ? t("opening") : t("openProject")}</button></div>
        </form>
      </section>
    </div>
  );
}
