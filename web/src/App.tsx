import { type CSSProperties, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowsClockwise, Lock, WarningCircle, X } from "@phosphor-icons/react";
import { ApiError, applyProductUpdate, checkProductUpdate, clearRecentProjectHistory, getDevelopmentActivity, getInspectionProgress, getLiveDocuments, getProductUpdateStatus, getRecentProjects, getRule5Candidates, getSnapshot, openProject, pasteProjectPath, pickProjectDirectory, rescanProject, revealPath } from "./api";
import { CommandBar } from "./components/CommandBar";
import { InspectorPane } from "./components/InspectorPane";
import { Overview } from "./components/Overview";
import { ProjectDialog } from "./components/ProjectDialog";
import { RepositoryTree } from "./components/RepositoryTree";
import { StatusBar } from "./components/StatusBar";
import { UpdateNotice } from "./components/UpdateNotice";
import { useI18n } from "./i18n";
import { packetWorkItems } from "./packetWork";
import { selectionFor } from "./selection";
import { useTheme } from "./theme";
import type { DevelopmentActivity, InspectionProgress, LiveDocuments, ProductUpdateStatus, RecentProject, RescanMode, Rule5Candidates, Snapshot } from "./types";

type LoadState = "loading" | "ready" | "error";
type WorkspaceStyle = CSSProperties & { "--repository-width": string; "--inspector-width": string };
const MIN_PROGRESS_VISIBILITY_MS = 700;
const AUTO_INTERVAL_SECONDS = 15;
const RESCAN_MODE_KEY = "sdad-inspector:rescan-mode:v1";
const PANE_WIDTHS_KEY = "sdad-inspector:pane-widths:v1";
const UPDATE_APPLY_DELAY_SECONDS = 10;
const UPDATE_RECHECK_MS = 6 * 60 * 60 * 1000;

async function loadWorkspaceSignals(): Promise<{ documents: LiveDocuments | null; activity: DevelopmentActivity | null; rule5: Rule5Candidates | null }> {
  const [documents, activity, rule5] = await Promise.allSettled([getLiveDocuments(), getDevelopmentActivity(), getRule5Candidates()]);
  return {
    documents: documents.status === "fulfilled" && Array.isArray(documents.value.documents) ? documents.value : null,
    activity: activity.status === "fulfilled" && Array.isArray(activity.value.files) && Array.isArray(activity.value.commits) && Array.isArray(activity.value.handoffs) ? activity.value : null,
    rule5: rule5.status === "fulfilled" && Array.isArray(rule5.value.candidates) ? rule5.value : null,
  };
}

function initialRescanMode(): RescanMode {
  try { return localStorage.getItem(RESCAN_MODE_KEY) === "auto" ? "auto" : "manual"; } catch { return "manual"; }
}

function initialPaneWidths(): { repository: number; inspector: number } {
  try {
    const parsed = JSON.parse(localStorage.getItem(PANE_WIDTHS_KEY) ?? "null");
    if (typeof parsed?.repository === "number" && typeof parsed?.inspector === "number") {
      return { repository: Math.min(430, Math.max(240, parsed.repository)), inspector: Math.min(480, Math.max(280, parsed.inspector)) };
    }
  } catch { /* use readable defaults */ }
  return { repository: 280, inspector: 320 };
}

export function App() {
  const { t } = useI18n();
  const { theme, toggleTheme } = useTheme();
  const tRef = useRef(t);
  useEffect(() => { tRef.current = t; }, [t]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState("overview");
  const [projectDialog, setProjectDialog] = useState(false);
  const [repositoryOpen, setRepositoryOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const [inspectionProgress, setInspectionProgress] = useState<InspectionProgress | null>(null);
  const [liveDocuments, setLiveDocuments] = useState<LiveDocuments | null>(null);
  const [activity, setActivity] = useState<DevelopmentActivity | null>(null);
  const [rule5, setRule5] = useState<Rule5Candidates | null>(null);
  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);
  const [rescanMode, setRescanModeState] = useState<RescanMode>(initialRescanMode);
  const [autoSeconds, setAutoSeconds] = useState(AUTO_INTERVAL_SECONDS);
  const [paneWidths, setPaneWidths] = useState(initialPaneWidths);
  const [productUpdate, setProductUpdate] = useState<ProductUpdateStatus | null>(null);
  const [updateCountdown, setUpdateCountdown] = useState<number | null>(null);
  const [updatePostponed, setUpdatePostponed] = useState(false);
  const workspaceRef = useRef<HTMLDivElement>(null);
  const autoDeadline = useRef(Date.now() + AUTO_INTERVAL_SECONDS * 1000);
  const rescanAction = useRef<() => Promise<void>>(async () => undefined);
  const updateApplyStarted = useRef(false);

  const load = useCallback(async () => {
    setLoadState("loading"); setError(null);
    try {
      const [next, signals, recent] = await Promise.all([
        getSnapshot(),
        loadWorkspaceSignals(),
        getRecentProjects().catch(() => []),
      ]);
      setSnapshot(next); setLiveDocuments(signals.documents); setActivity(signals.activity); setRule5(signals.rule5); setRecentProjects(recent); setLoadState("ready");
    }
    catch (reason) { setLoadState("error"); setError(reason instanceof Error ? reason.message : tRef.current("snapshotLoadFailed")); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const checkForProductUpdate = useCallback(async (force = false) => {
    try {
      const next = await checkProductUpdate(force);
      setProductUpdate(next);
      if (next.state !== "ready") setUpdatePostponed(false);
    } catch {
      // Product update availability never blocks local inspection.
    }
  }, []);

  useEffect(() => {
    void checkForProductUpdate();
    const timer = window.setInterval(() => void checkForProductUpdate(), UPDATE_RECHECK_MS);
    return () => window.clearInterval(timer);
  }, [checkForProductUpdate]);

  useEffect(() => {
    if (!productUpdate || !["checking", "downloading", "applying"].includes(productUpdate.state)) return undefined;
    let stopped = false;
    const timer = window.setInterval(() => {
      void getProductUpdateStatus().then((next) => { if (!stopped) setProductUpdate(next); }).catch(() => undefined);
    }, 650);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [productUpdate?.state]);

  useEffect(() => {
    if (productUpdate?.state !== "ready" || updatePostponed || busy) {
      setUpdateCountdown(null);
      return undefined;
    }
    const deadline = Date.now() + UPDATE_APPLY_DELAY_SECONDS * 1000;
    setUpdateCountdown(UPDATE_APPLY_DELAY_SECONDS);
    const timer = window.setInterval(() => {
      setUpdateCountdown(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)));
    }, 250);
    return () => window.clearInterval(timer);
  }, [productUpdate?.state, productUpdate?.available_version, updatePostponed, busy]);

  async function handleProductUpdateApply() {
    if (busy || updateApplyStarted.current || productUpdate?.state !== "ready") return;
    updateApplyStarted.current = true;
    setUpdateCountdown(null);
    try {
      const next = await applyProductUpdate();
      setProductUpdate(next);
      setAnnouncement(t("updateApplying"));
    } catch (reason) {
      const message = reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("updateFailedDetail");
      setProductUpdate((current) => current ? { ...current, state: "error", error: message, message: null } : current);
      setAnnouncement(message);
      updateApplyStarted.current = false;
    }
  }

  useEffect(() => {
    if (updateCountdown === 0) void handleProductUpdateApply();
  }, [updateCountdown]);

  useEffect(() => {
    if (!busy) return undefined;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try { const next = await getInspectionProgress(); if (!stopped) setInspectionProgress(next); }
      catch { /* operation request owns user-facing failures */ }
      finally { if (!stopped) timer = setTimeout(() => void poll(), 140); }
    }
    void poll();
    return () => { stopped = true; if (timer) clearTimeout(timer); };
  }, [busy]);

  async function finishProgressFeedback(startedAt: number) {
    try { setInspectionProgress(await getInspectionProgress()); } catch { /* completed operation remains authoritative */ }
    const remaining = MIN_PROGRESS_VISIBILITY_MS - (performance.now() - startedAt);
    if (remaining > 0) await new Promise((resolve) => setTimeout(resolve, remaining));
  }

  function resetAutoCountdown() {
    autoDeadline.current = Date.now() + AUTO_INTERVAL_SECONDS * 1000;
    setAutoSeconds(AUTO_INTERVAL_SECONDS);
  }

  async function handleRescan() {
    if (busy) return;
    resetAutoCountdown();
    const startedAt = performance.now();
    setInspectionProgress(null); setBusy(true); setError(null); setAnnouncement(t("rescanStarted"));
    try {
      const next = await rescanProject();
      const signals = await loadWorkspaceSignals();
      await finishProgressFeedback(startedAt);
      setSnapshot(next);
      if (signals.documents) setLiveDocuments(signals.documents);
      if (signals.activity) setActivity(signals.activity);
      if (signals.rule5) setRule5(signals.rule5);
      setLoadState("ready");
      setAnnouncement(t("rescanComplete", { errors: next.doctor.summary.errors, warnings: next.doctor.summary.warnings }));
    } catch (reason) {
      const message = reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("rescanFailed");
      setError(message); setAnnouncement(message);
    } finally { setBusy(false); resetAutoCountdown(); }
  }
  rescanAction.current = handleRescan;

  useEffect(() => {
    resetAutoCountdown();
    if (rescanMode !== "auto") return undefined;
    const tick = () => {
      if (document.visibilityState !== "visible" || busy) { resetAutoCountdown(); return; }
      const remaining = Math.max(0, Math.ceil((autoDeadline.current - Date.now()) / 1000));
      setAutoSeconds(remaining);
      if (remaining === 0) { resetAutoCountdown(); void rescanAction.current(); }
    };
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [rescanMode, snapshot?.project.root, busy]);

  function setRescanMode(mode: RescanMode) {
    setRescanModeState(mode); resetAutoCountdown();
    try { localStorage.setItem(RESCAN_MODE_KEY, mode); } catch { /* active session still changes */ }
  }

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const editing = target?.matches("input, textarea, [contenteditable='true']");
      if (event.key === "/" && !editing) { event.preventDefault(); document.querySelector<HTMLInputElement>("#repository-filter")?.focus(); }
      if (event.altKey && event.key.toLocaleLowerCase() === "r" && !editing && !busy) { event.preventDefault(); void handleRescan(); }
      if (event.key === "Escape") { setProjectDialog(false); setRepositoryOpen(false); setInspectorOpen(false); }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  });

  async function handleOpenProject(projectRoot: string) {
    if (busy) return;
    resetAutoCountdown();
    const startedAt = performance.now();
    setInspectionProgress(null); setBusy(true); setError(null);
    try {
      const next = await openProject(projectRoot);
      const [signals, recent] = await Promise.all([
        loadWorkspaceSignals(),
        getRecentProjects().catch(() => []),
      ]);
      await finishProgressFeedback(startedAt);
      setSnapshot(next); setLiveDocuments(signals.documents); setActivity(signals.activity); setRule5(signals.rule5); setRecentProjects(recent); setSelectedId("overview"); setProjectDialog(false);
      setAnnouncement(t("openedProject", { project: next.project.name }));
    } catch (reason) {
      const message = reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("projectOpenFailed");
      setError(message); setAnnouncement(message);
    } finally { setBusy(false); resetAutoCountdown(); }
  }

  async function copy(value: string, label: string) {
    try { await navigator.clipboard.writeText(value); setAnnouncement(t("copied", { label })); }
    catch { setAnnouncement(t("copyFailed", { label })); }
  }

  async function handleClearRecent() {
    try {
      setRecentProjects(await clearRecentProjectHistory());
      setAnnouncement(t("historyCleared"));
    } catch (reason) {
      const message = reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("historyClearFailed");
      setError(message); setAnnouncement(message);
    }
  }

  async function reveal(relative: string) {
    try { await revealPath(relative); setAnnouncement(t("locationOpened")); }
    catch (reason) { const message = reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("locationRevealFailed"); setError(message); setAnnouncement(message); }
  }

  function persistPaneWidths(next: { repository: number; inspector: number }) {
    setPaneWidths(next);
    try { localStorage.setItem(PANE_WIDTHS_KEY, JSON.stringify(next)); } catch { /* active drag still works */ }
  }

  function startResize(side: "repository" | "inspector", event: ReactPointerEvent<HTMLDivElement>) {
    if (!workspaceRef.current || window.innerWidth <= 760) return;
    event.preventDefault();
    const rect = workspaceRef.current.getBoundingClientRect();
    let next = paneWidths;
    const move = (pointer: PointerEvent) => {
      const value = side === "repository" ? pointer.clientX - rect.left : rect.right - pointer.clientX;
      next = side === "repository"
        ? { ...next, repository: Math.min(430, Math.max(240, value)) }
        : { ...next, inspector: Math.min(480, Math.max(280, value)) };
      setPaneWidths(next);
    };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); persistPaneWidths(next); };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up, { once: true });
  }

  function resizeWithKeyboard(side: "repository" | "inspector", event: ReactKeyboardEvent<HTMLDivElement>) {
    if (!(["ArrowLeft", "ArrowRight", "Home"] as string[]).includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Home") { persistPaneWidths(side === "repository" ? { ...paneWidths, repository: 280 } : { ...paneWidths, inspector: 320 }); return; }
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const delta = side === "repository" ? direction * 16 : direction * -16;
    persistPaneWidths(side === "repository"
      ? { ...paneWidths, repository: Math.min(430, Math.max(240, paneWidths.repository + delta)) }
      : { ...paneWidths, inspector: Math.min(480, Math.max(280, paneWidths.inspector + delta)) });
  }

  const packetWork = useMemo(() => {
    if (!snapshot) return [];
    const todo = liveDocuments?.documents.find((document) => document.roles.includes("todo"));
    return packetWorkItems(todo?.content, snapshot.state.active_packet?.id);
  }, [snapshot, liveDocuments]);
  const selection = useMemo(() => snapshot ? selectionFor(snapshot, selectedId, t, packetWork) : null, [snapshot, selectedId, t, packetWork]);

  if (loadState === "loading" && !snapshot) return <div className="loading-shell" aria-busy="true"><div className="loading-brand"><img src="/sdad-inspector-logo.png" alt="" /><strong>SDAD Inspector</strong></div><div className="loading-grid"><div /><div /><div /></div><p><ArrowsClockwise className="spin" size={19} /> {t("inspectingRepository")}</p></div>;

  if (loadState === "error" && !snapshot) return <main className="error-surface"><span className="error-icon"><WarningCircle size={28} /></span><p className="section-kicker">{t("localInspectionUnavailable")}</p><h1>{t("couldNotLoadProject")}</h1><p>{error}</p><button onClick={() => void load()}><ArrowsClockwise size={18} /> {t("tryAgain")}</button><small><Lock size={15} /> {t("noWriteAttempted")}</small></main>;

  if (!snapshot || !selection) return null;
  const workspaceStyle: WorkspaceStyle = { "--repository-width": `${paneWidths.repository}px`, "--inspector-width": `${paneWidths.inspector}px` };
  return (
    <div className="app-shell">
      <CommandBar snapshot={snapshot} busy={busy} onRescan={() => void handleRescan()} onReveal={() => void reveal(".")} onCopy={() => void copy(snapshot.project.root, t("projectPath"))} onOpenProject={() => setProjectDialog(true)} onCopySnapshot={() => void copy(JSON.stringify(snapshot, null, 2), t("labelSnapshotJson"))} onToggleRepository={() => setRepositoryOpen((value) => !value)} onToggleInspector={() => setInspectorOpen((value) => !value)} theme={theme} onToggleTheme={toggleTheme} rescanMode={rescanMode} autoSeconds={autoSeconds} onRescanModeChange={setRescanMode} update={productUpdate} onCheckUpdate={() => void checkForProductUpdate(true)} />
      <UpdateNotice status={productUpdate} countdown={updateCountdown} inspectionBusy={busy} postponed={updatePostponed} onApply={() => void handleProductUpdateApply()} onPostpone={() => setUpdatePostponed(true)} onRetry={() => { updateApplyStarted.current = false; setUpdatePostponed(false); void checkForProductUpdate(true); }} />
      {error && <div className="inline-error" role="alert"><WarningCircle size={17} />{error}<button onClick={() => setError(null)} aria-label={t("dismissError")}><X size={18} /></button></div>}
      <div className="workspace" ref={workspaceRef} style={workspaceStyle}>
        {(repositoryOpen || inspectorOpen) && <button className="mobile-scrim" aria-label={t("closeOpenPane")} onClick={() => { setRepositoryOpen(false); setInspectorOpen(false); }} />}
        <RepositoryTree snapshot={snapshot} selectedId={selectedId} onSelect={(id) => { setSelectedId(id); setRepositoryOpen(false); setInspectorOpen(false); }} mobileOpen={repositoryOpen} onCloseMobile={() => setRepositoryOpen(false)} activity={activity} packetWork={packetWork} rule5={rule5} />
        <div className="pane-resizer repository-resizer" role="separator" aria-orientation="vertical" aria-label={t("resizeRepository")} aria-valuemin={240} aria-valuemax={430} aria-valuenow={Math.round(paneWidths.repository)} tabIndex={0} title={t("resetPaneWidth")} onPointerDown={(event) => startResize("repository", event)} onKeyDown={(event) => resizeWithKeyboard("repository", event)} onDoubleClick={() => persistPaneWidths({ ...paneWidths, repository: 280 })}><span /></div>
        <Overview snapshot={snapshot} selectedId={selectedId} selection={selection} busy={busy} progress={inspectionProgress} onSelect={setSelectedId} liveDocuments={liveDocuments} activity={activity} packetWork={packetWork} rule5={rule5} />
        <div className="pane-resizer inspector-resizer" role="separator" aria-orientation="vertical" aria-label={t("resizeInspector")} aria-valuemin={280} aria-valuemax={480} aria-valuenow={Math.round(paneWidths.inspector)} tabIndex={0} title={t("resetPaneWidth")} onPointerDown={(event) => startResize("inspector", event)} onKeyDown={(event) => resizeWithKeyboard("inspector", event)} onDoubleClick={() => persistPaneWidths({ ...paneWidths, inspector: 320 })}><span /></div>
        <InspectorPane snapshot={snapshot} selection={selection} onReveal={(path) => void reveal(path)} onCopy={(value, label) => void copy(value, label)} mobileOpen={inspectorOpen} onCloseMobile={() => setInspectorOpen(false)} />
      </div>
      <StatusBar snapshot={snapshot} />
      <ProjectDialog currentPath={snapshot.project.root} open={projectDialog} busy={busy} recentProjects={recentProjects.filter((project) => project.path.toLocaleLowerCase() !== snapshot.project.root.toLocaleLowerCase())} onClose={() => setProjectDialog(false)} onSubmit={(path) => void handleOpenProject(path)} onBrowse={async (initialPath) => (await pickProjectDirectory(initialPath)).project_root} onPaste={async () => (await pasteProjectPath()).project_root} onClearRecent={() => void handleClearRecent()} />
      <div className="sr-only" aria-live="polite">{announcement}</div>
    </div>
  );
}
