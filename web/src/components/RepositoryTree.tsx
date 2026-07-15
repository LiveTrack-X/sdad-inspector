import { type KeyboardEvent, type ReactNode, useMemo, useRef, useState } from "react";
import {
  CaretDown,
  CaretRight,
  ChartLineUp,
  CheckCircle,
  Circle,
  Cube,
  FileCode,
  FileText,
  Folder,
  FunnelSimple,
  MagnifyingGlass,
  Shield,
  Stack,
  BookOpenText,
  House,
  X,
} from "@phosphor-icons/react";
import { useI18n } from "../i18n";
import type { PacketWorkItem } from "../packetWork";
import type { DevelopmentActivity, Rule5Candidates, Snapshot } from "../types";

interface NodeData {
  id: string;
  label: string;
  icon: ReactNode;
  value?: string | number;
  tone?: "success" | "warning" | "error" | "accent" | "muted";
  children?: NodeData[];
}

interface Props {
  snapshot: Snapshot;
  selectedId: string;
  onSelect: (id: string) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  activity: DevelopmentActivity | null;
  packetWork: PacketWorkItem[];
  rule5: Rule5Candidates | null;
}

export function RepositoryTree({ snapshot, selectedId, onSelect, mobileOpen, onCloseMobile, activity, packetWork, rule5 }: Props) {
  const { t } = useI18n();
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState(() => new Set(["documents", "findings", "evidence"]));
  const treeRef = useRef<HTMLDivElement>(null);
  const errorCount = snapshot.doctor.findings.filter((item) => item.severity === "error").length;
  const warningCount = snapshot.doctor.findings.filter((item) => item.severity === "warning").length;
  const handoff = snapshot.state.current_handoff;
  const routedDocuments = Array.from(new Set(snapshot.state.routed_docs.filter((path) => path.toLocaleLowerCase().endsWith(".md"))));
  const nodes = useMemo<NodeData[]>(() => [
    { id: "overview", label: t("overview"), icon: <House size={19} weight="duotone" />, tone: "accent" },
    {
      id: "state",
      label: t("state"),
      icon: <CheckCircle size={19} weight="duotone" />,
      value: snapshot.state.active_packet?.status ?? t("unavailable"),
      tone: snapshot.doctor.summary.errors ? "error" : "success",
    },
    { id: "spec", label: t("activeSpec"), icon: <FileText size={19} />, value: snapshot.state.active_spec?.path ?? t("none"), tone: "accent" },
    { id: "packet", label: t("activePacketThisRepo"), icon: <Cube size={19} />, value: snapshot.state.active_packet?.id ?? t("none"), tone: "accent" },
    { id: "todo", label: t("todo"), icon: <Circle size={18} />, value: packetWork.filter((item) => !item.completed).length, tone: "muted" },
    {
      id: "development",
      label: t("developmentFlow"),
      icon: <ChartLineUp size={19} weight="duotone" />,
      value: activity ? activity.changed_count : t("liveInspection"),
      tone: activity?.changed_count ? "warning" : activity?.available ? "success" : "muted",
    },
    { id: "rule5", label: t("rule5Title"), icon: <FunnelSimple size={19} weight="duotone" />, value: rule5?.candidates.length ?? 0, tone: rule5?.candidates.length ? "warning" : "muted" },
    {
      id: "documents",
      label: t("documents"),
      icon: <BookOpenText size={19} />,
      value: routedDocuments.length,
      tone: "muted",
      children: routedDocuments.map((path) => ({
        id: `doc:${encodeURIComponent(path)}`,
        label: path,
        icon: <FileText size={18} />,
        tone: "muted" as const,
      })),
    },
    {
      id: "findings",
      label: t("reviewFindings"),
      icon: <Shield size={19} />,
      value: snapshot.doctor.findings.length,
      tone: snapshot.doctor.findings.length ? "warning" : "success",
      children: [
        { id: "findings-errors", label: t("errors"), icon: <span className="branch-line" />, value: errorCount, tone: "error" },
        { id: "findings-warnings", label: t("warnings"), icon: <span className="branch-line" />, value: warningCount, tone: "warning" },
        { id: "findings-notes", label: t("notes"), icon: <span className="branch-line" />, value: Math.max(0, snapshot.doctor.findings.length - errorCount - warningCount), tone: "accent" },
      ],
    },
    {
      id: "handoff",
      label: t("currentHandoff"),
      icon: <Stack size={19} />,
      value: handoff?.declared ? (handoff.exists ? t("present") : t("missing")) : t("none"),
      tone: handoff?.declared && !handoff.exists ? "warning" : "muted",
    },
    {
      id: "evidence",
      label: t("evidence"),
      icon: <Folder size={19} />,
      children: [
        { id: "evidence-doctor", label: t("doctorReportJson"), icon: <FileCode size={18} />, value: 1, tone: "muted" },
        { id: "evidence-state", label: t("stateYaml"), icon: <FileText size={18} />, value: snapshot.state.available ? 1 : 0, tone: "muted" },
        { id: "evidence-spec", label: t("activeSpecMarkdown"), icon: <FileText size={18} />, value: snapshot.state.active_spec?.exists ? 1 : 0, tone: "muted" },
        { id: "evidence-todo", label: t("todoMarkdown"), icon: <FileText size={18} />, value: 1, tone: "muted" },
        { id: "evidence-findings", label: t("findingsMarkdown"), icon: <FileText size={18} />, value: 1, tone: "muted" },
        { id: "evidence-handoff", label: t("handoffMarkdown"), icon: <FileText size={18} />, value: handoff?.exists ? 1 : 0, tone: "muted" },
        { id: "evidence-snapshot", label: t("snapshotJson"), icon: <FileCode size={18} />, value: 1, tone: "muted" },
      ],
    },
  ], [snapshot, handoff, errorCount, warningCount, routedDocuments, activity, packetWork, rule5, t]);

  const visibleNodes = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase();
    if (!query) return nodes;
    return nodes.flatMap((node) => {
      const children = node.children?.filter((child) => child.label.toLocaleLowerCase().includes(query));
      if (node.label.toLocaleLowerCase().includes(query) || children?.length) {
        return [{ ...node, children }];
      }
      return [];
    });
  }, [nodes, filter]);

  function toggle(id: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(treeRef.current?.querySelectorAll<HTMLButtonElement>("[data-tree-node]") ?? []);
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "ArrowDown" && index >= 0) {
      event.preventDefault(); items[Math.min(index + 1, items.length - 1)]?.focus();
    } else if (event.key === "ArrowUp" && index >= 0) {
      event.preventDefault(); items[Math.max(index - 1, 0)]?.focus();
    }
  }

  return (
    <aside className={`repository-pane ${mobileOpen ? "mobile-open" : ""}`} aria-label={t("repositoryControls")}>
      <div className="pane-title-row">
        <h2>{t("repository")}</h2>
        <button className="mobile-close" onClick={onCloseMobile} aria-label={t("closeRepositoryControls")}><X size={18} /></button>
      </div>
      <div className="filter-row">
        <label className="filter-input">
          <MagnifyingGlass size={18} />
          <span className="sr-only">{t("filterControls")}</span>
          <input id="repository-filter" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder={t("filterControls")} />
          {filter && <button onClick={() => setFilter("")} aria-label={t("clearFilter")}><X size={15} /></button>}
        </label>
        <button className="icon-button filter-button" aria-label={t("filterOptions")} title={t("textFilterActive")}><FunnelSimple size={20} /></button>
      </div>
      <div className="tree" role="tree" ref={treeRef} onKeyDown={handleKeyDown}>
        {visibleNodes.map((node) => {
          const open = Boolean(node.children && (expanded.has(node.id) || filter));
          return (
            <div className="tree-group" key={node.id}>
              <button
                data-tree-node
                role="treeitem"
                aria-expanded={node.children ? open : undefined}
                aria-current={selectedId === node.id ? "true" : undefined}
                className={`tree-node ${selectedId === node.id ? "selected" : ""}`}
                onClick={() => { onSelect(node.id); if (node.children) toggle(node.id); }}
              >
                <span className="tree-caret">{node.children ? (open ? <CaretDown size={13} /> : <CaretRight size={13} />) : null}</span>
                <span className="tree-icon">{node.icon}</span>
                <span className="tree-label">{node.label}</span>
                {node.value !== undefined && <span className={`tree-value ${node.tone ?? ""}`}>{node.value}</span>}
              </button>
              {open && node.children && (
                <div role="group" className="tree-children">
                  {node.children.map((child) => (
                    <button
                      data-tree-node
                      role="treeitem"
                      aria-current={selectedId === child.id ? "true" : undefined}
                      className={`tree-node child ${selectedId === child.id ? "selected" : ""}`}
                      key={child.id}
                      onClick={() => onSelect(child.id)}
                    >
                      <span className="tree-caret" />
                      <span className="tree-icon child-marker">{child.icon}</span>
                      <span className="tree-label">{child.label}</span>
                      <span className={`tree-value ${child.tone ?? ""}`}>{child.value}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {!visibleNodes.length && <p className="tree-empty">{t("noControlsMatch", { query: filter })}</p>}
      </div>
      <div className="tree-footer">
        <button onClick={() => setExpanded(new Set(nodes.filter((node) => node.children).map((node) => node.id)))}>{t("expandAll")}</button>
        <button onClick={() => setExpanded(new Set())}>{t("collapseAll")}</button>
      </div>
    </aside>
  );
}
