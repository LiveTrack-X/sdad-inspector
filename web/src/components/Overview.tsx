import { type ReactNode, useLayoutEffect, useRef, useState } from "react";
import {
  CheckCircle,
  BookOpenText,
  CaretDown,
  Cube,
  Database,
  FileText,
  Folder,
  Info,
  Shield,
  Stack,
  WarningCircle,
} from "@phosphor-icons/react";
import { type Translate, useI18n } from "../i18n";
import type { PacketWorkItem } from "../packetWork";
import { documentPathForSelection, documentSelectionId } from "../selection";
import { formatAbsolute } from "../time";
import type { DevelopmentActivity, FieldSelection, InspectionProgress as Progress, LiveDocuments, Rule5Candidates, Snapshot } from "../types";
import { DevelopmentFlowView, PacketEvidencePanel } from "./DevelopmentFlow";
import { InspectionProgress } from "./InspectionProgress";
import { MarkdownViewer } from "./MarkdownViewer";
import { Rule5View } from "./Rule5View";

interface Props {
  snapshot: Snapshot;
  selectedId: string;
  selection: FieldSelection;
  busy: boolean;
  progress: Progress | null;
  onSelect: (id: string) => void;
  liveDocuments: LiveDocuments | null;
  activity: DevelopmentActivity | null;
  packetWork: PacketWorkItem[];
  rule5: Rule5Candidates | null;
}

interface Fact {
  label: string;
  value: string | number;
  mono?: boolean;
  tone?: "success" | "warning" | "error";
}

function relationshipLabel(kind: string, t: Translate): string {
  if (kind === "active_spec_to_packet") return t("relationshipActiveSpec");
  if (kind === "validation_for_packet") return t("relationshipValidation");
  if (kind === "handoff_to_packet") return t("relationshipHandoff");
  return kind;
}

function relationshipSelectionId(snapshot: Snapshot, path: string | null): string | null {
  if (!path || !path.toLocaleLowerCase().endsWith(".md")) return null;
  if (path === snapshot.state.active_spec?.path) return "spec";
  if (path === snapshot.protocol.todo_path) return "todo";
  const eligible = new Set([
    ...snapshot.state.routed_docs,
    snapshot.state.current_handoff?.path,
  ].filter((item): item is string => Boolean(item)));
  return eligible.has(path) ? `doc:${encodeURIComponent(path)}` : null;
}

function FactList({ facts }: { facts: Fact[] }) {
  return (
    <dl className="context-facts">
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt>{fact.label}</dt>
          <dd className={`${fact.mono ? "mono" : ""} ${fact.tone ?? ""}`}>{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ContextHeader({
  icon,
  kicker,
  title,
  description,
}: {
  icon: ReactNode;
  kicker: string;
  title: string;
  description: string;
}) {
  return (
    <header className="context-header">
      <span className="context-icon">{icon}</span>
      <div>
        <p className="section-kicker">{kicker}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </header>
  );
}

function StateView({ snapshot }: { snapshot: Snapshot }) {
  const { t } = useI18n();
  const state = snapshot.state;
  return (
    <div className="context-view">
      <ContextHeader
        icon={<CheckCircle size={24} weight="duotone" />}
        kicker={t("repositoryControl")}
        title={t("repositoryState")}
        description={t("stateViewDescription")}
      />
      <section className="context-section" aria-labelledby="state-contract-heading">
        <h2 id="state-contract-heading">{t("packetExecution")}</h2>
        <FactList facts={[
          { label: t("availability"), value: state.available ? t("available") : t("missing"), tone: state.available ? "success" : "error" },
          { label: t("stateSchema"), value: state.schema_version ?? "—", mono: true },
          { label: t("scale"), value: state.scale ?? t("notDeclared"), mono: true },
          { label: t("executionScope"), value: state.execution_scope ?? t("notDeclared"), mono: true },
          { label: t("activePacket"), value: state.active_packet?.id ?? t("notDeclared"), mono: true },
          { label: t("observedValue"), value: state.active_packet?.status ?? t("unavailable"), mono: true },
        ]} />
      </section>
      <section className="context-section" aria-labelledby="version-contract-heading">
        <h2 id="version-contract-heading">{t("versionContracts")}</h2>
        <FactList facts={[
          { label: t("inspectorVersion"), value: snapshot.inspector_version, mono: true },
          { label: t("engineVersion"), value: snapshot.protocol.engine_display_name, mono: true },
          { label: t("reportSchema"), value: snapshot.contracts.report_schema_version, mono: true },
          { label: t("snapshotSchemaLabel"), value: snapshot.snapshot_schema_version, mono: true },
        ]} />
      </section>
      <section className="context-section" aria-labelledby="state-gates-heading">
        <h2 id="state-gates-heading">{t("declaredOwnerGates")}</h2>
        {state.owner_gates.length ? (
          <ul className="simple-list gate-list">
            {state.owner_gates.map((gate) => <li key={gate}><Shield size={17} /><code>{gate}</code><span>{t("approvalUnobserved")}</span></li>)}
          </ul>
        ) : <p className="empty-copy">{t("noOwnerGate")}</p>}
      </section>
    </div>
  );
}

function DocumentView({ snapshot, selectedId, liveDocuments, onSelect }: { snapshot: Snapshot; selectedId: string; liveDocuments: LiveDocuments | null; onSelect: (id: string) => void }) {
  const { locale, t } = useI18n();
  const [routesOpen, setRoutesOpen] = useState(() => (
    typeof window === "undefined"
    || typeof window.matchMedia !== "function"
    || window.matchMedia("(min-width: 761px)").matches
  ));
  const path = documentPathForSelection(snapshot, selectedId);
  const document = liveDocuments?.documents.find((item) => item.path === path);
  const routed = Array.from(new Set(snapshot.state.routed_docs.filter((item) => item.toLocaleLowerCase().endsWith(".md"))));
  return (
    <div className="context-view document-view">
      <header className="document-header">
        <span className="context-icon"><BookOpenText size={25} /></span>
        <div><p className="section-kicker">{t("liveDocument")}</p><h1>{path ?? t("documentUnavailable")}</h1><p>{liveDocuments ? t("readAt", { time: formatAbsolute(liveDocuments.read_at, locale) }) : t("inspectingRepository")}</p></div>
      </header>
      {routed.length > 0 && (
        <nav className={`document-route-list ${routesOpen ? "open" : ""}`} aria-label={t("routedDocuments")}>
          <button
            type="button"
            className="document-route-toggle"
            aria-expanded={routesOpen}
            aria-controls="routed-document-options"
            aria-label={t(routesOpen ? "hideRoutedDocuments" : "showRoutedDocuments", { count: routed.length })}
            onClick={() => setRoutesOpen((value) => !value)}
          >
            <span><strong>{t("routedDocuments")}</strong><span>{t("routedDocumentsDescription")}</span></span>
            <span className="document-route-count">{routed.length}</span>
            <CaretDown size={18} />
          </button>
          {routesOpen && <ul id="routed-document-options">{routed.map((route) => <li key={route}><button className={route === path ? "active" : ""} onClick={() => onSelect(documentSelectionId(snapshot, route))} title={t("clickToRead")}><FileText size={18} /><code>{route}</code></button></li>)}</ul>}
        </nav>
      )}
      <section className="document-reader" aria-label={path ?? t("documents")}>
        {document ? <MarkdownViewer document={document} navigation /> : <div className="document-empty">{liveDocuments ? t("documentUnavailable") : t("inspectingRepository")}</div>}
      </section>
    </div>
  );
}

function FindingsView({ snapshot, selectedId, title }: { snapshot: Snapshot; selectedId: string; title: string }) {
  const { t } = useI18n();
  const severity = selectedId === "findings-errors" ? "error" : selectedId === "findings-warnings" ? "warning" : selectedId === "findings-notes" ? "note" : null;
  const findings = severity ? snapshot.doctor.findings.filter((finding) => finding.severity === severity) : snapshot.doctor.findings;
  const errors = snapshot.doctor.findings.filter((finding) => finding.severity === "error").length;
  const warnings = snapshot.doctor.findings.filter((finding) => finding.severity === "warning").length;
  const notes = snapshot.doctor.findings.length - errors - warnings;
  return (
    <div className="context-view">
      <ContextHeader icon={<Shield size={24} />} kicker={t("doctorFindingAuthority")} title={title} description={t("findingsViewDescription")} />
      <div className="finding-count-strip" aria-label={t("doctorFindings")}>
        <span><strong>{errors}</strong>{t("errors")}</span>
        <span><strong>{warnings}</strong>{t("warnings")}</span>
        <span><strong>{notes}</strong>{t("notes")}</span>
      </div>
      <section className="context-section" aria-labelledby="selected-findings-heading">
        <h2 id="selected-findings-heading">{severity ? title : t("allSeverities")}</h2>
        {findings.length ? (
          <ul className="context-finding-list">
            {findings.map((finding) => (
              <li className={`severity-${finding.severity}`} key={`${finding.id}-${finding.path}-${finding.line ?? 0}`}>
                <div className="finding-title-row"><strong>{finding.id}</strong><span>{finding.severity}</span></div>
                <p>{finding.message}</p>
                <code>{finding.path}{finding.line ? `:${finding.line}` : ""}</code>
                <dl>
                  <div><dt>{t("findingEvidence")}</dt><dd>{finding.evidence}</dd></div>
                  <div><dt>{t("findingRemediation")}</dt><dd>{finding.remediation}</dd></div>
                </dl>
              </li>
            ))}
          </ul>
        ) : (
          <div className="context-empty"><CheckCircle size={23} /><p>{t("noFindingsForSelection")}</p></div>
        )}
      </section>
    </div>
  );
}

function HandoffView({ snapshot }: { snapshot: Snapshot }) {
  const { t } = useI18n();
  const handoff = snapshot.state.current_handoff;
  const relationship = snapshot.relationships.find((item) => item.kind === "handoff_to_packet");
  return (
    <div className="context-view">
      <ContextHeader icon={<Stack size={24} />} kicker={t("continuity")} title={t("currentHandoff")} description={t("handoffViewDescription")} />
      <section className="context-section" aria-labelledby="handoff-state-heading">
        <h2 id="handoff-state-heading">{t("declaration")}</h2>
        <FactList facts={[
          { label: t("declaration"), value: handoff?.declared ? t("declaredPresent") : t("notDeclared") },
          { label: t("declaredPath"), value: handoff?.path ?? t("notDeclared"), mono: true },
          { label: t("fileStatus"), value: handoff?.exists ? t("present") : t("missing"), tone: handoff?.exists ? undefined : "warning" },
          { label: t("relationshipToPacket"), value: relationship?.to ?? t("notDeclared"), mono: true },
          { label: t("observedValue"), value: relationship?.status ?? t("notDeclared"), mono: true },
        ]} />
        {!handoff?.declared && <div className="info-note"><Info size={20} /><p>{t("noHandoffDeclared")}</p></div>}
      </section>
    </div>
  );
}

function evidencePath(selectedId: string, snapshot: Snapshot): string | null {
  if (selectedId === "evidence-state") return snapshot.protocol.state_path;
  if (selectedId === "evidence-spec") return snapshot.state.active_spec?.path ?? null;
  if (selectedId === "evidence-todo") return snapshot.protocol.todo_path;
  if (selectedId === "evidence-findings") return snapshot.protocol.findings_path;
  if (selectedId === "evidence-handoff") return snapshot.state.current_handoff?.path ?? null;
  return null;
}

function EvidenceView({ snapshot, selectedId, selection }: { snapshot: Snapshot; selectedId: string; selection: FieldSelection }) {
  const { t } = useI18n();
  if (selectedId === "evidence") {
    return (
      <div className="context-view">
        <ContextHeader icon={<Folder size={24} />} kicker={t("preservedEvidence")} title={t("evidenceIndex")} description={t("evidenceViewDescription")} />
        <section className="context-section" aria-labelledby="evidence-sources-heading">
          <h2 id="evidence-sources-heading">{t("evidenceSources")}</h2>
          <ul className="evidence-file-list">
            {Object.entries(snapshot.evidence.files).map(([path, metadata]) => (
              <li key={path}>
                <FileText size={17} /><code>{path}</code>
                <span>{metadata.exists === false ? t("missing") : t("present")}</span>
              </li>
            ))}
            <li><Database size={17} /><code>{t("inMemoryDoctorJson")}</code><span>{t("present")}</span></li>
            <li><Database size={17} /><code>{t("inMemorySnapshot")}</code><span>{t("present")}</span></li>
          </ul>
        </section>
      </div>
    );
  }

  const path = evidencePath(selectedId, snapshot);
  const metadata = path ? snapshot.evidence.files[path] : undefined;
  const facts: Fact[] = selectedId === "evidence-doctor" ? [
    { label: t("engineVersion"), value: snapshot.protocol.engine_display_name, mono: true },
    { label: t("reportSchema"), value: snapshot.contracts.report_schema_version, mono: true },
    { label: t("doctorExitCode"), value: snapshot.doctor.exit_code, mono: true },
    { label: t("observedValue"), value: snapshot.doctor.completed ? t("completed") : snapshot.inspection_status, mono: true },
  ] : selectedId === "evidence-snapshot" ? [
    { label: t("inspectorVersion"), value: snapshot.inspector_version, mono: true },
    { label: t("snapshotSchemaLabel"), value: snapshot.snapshot_schema_version, mono: true },
    { label: t("inspectionIdentity"), value: snapshot.inspection_id, mono: true },
    { label: t("inspectedAt"), value: snapshot.inspected_at, mono: true },
  ] : [
    { label: t("declaredPath"), value: path ?? t("notDeclared"), mono: true },
    { label: t("fileStatus"), value: metadata?.exists === false || !metadata ? t("missing") : t("present"), tone: metadata?.exists === false || !metadata ? "warning" : "success" },
    ...(metadata?.bytes !== undefined ? [{ label: t("fileSize"), value: `${String(metadata.bytes)} B`, mono: true } as Fact] : []),
    ...(metadata?.sha256 ? [{ label: "SHA-256", value: String(metadata.sha256), mono: true } as Fact] : []),
  ];
  return (
    <div className="context-view">
      <ContextHeader icon={<Database size={24} />} kicker={t("selectedEvidence")} title={selection.label} description={t("selectedEvidenceDescription")} />
      <section className="context-section" aria-labelledby="evidence-metadata-heading">
        <h2 id="evidence-metadata-heading">{t("evidenceMetadata")}</h2>
        <FactList facts={facts} />
        <div className="info-note"><Info size={20} /><p>{t("readOnlyEvidenceNote")}</p></div>
      </section>
    </div>
  );
}

function ContextView({ snapshot, selectedId, selection, liveDocuments, activity, onSelect, packetWork, rule5 }: { snapshot: Snapshot; selectedId: string; selection: FieldSelection; liveDocuments: LiveDocuments | null; activity: DevelopmentActivity | null; onSelect: (id: string) => void; packetWork: PacketWorkItem[]; rule5: Rule5Candidates | null }) {
  if (selectedId === "state") return <StateView snapshot={snapshot} />;
  if (documentPathForSelection(snapshot, selectedId)) return <DocumentView snapshot={snapshot} selectedId={selectedId} liveDocuments={liveDocuments} onSelect={onSelect} />;
  if (selectedId === "development") return <DevelopmentFlowView snapshot={snapshot} documents={liveDocuments} activity={activity} work={packetWork} onSelect={onSelect} />;
  if (selectedId === "rule5") return <Rule5View data={rule5} />;
  if (selectedId === "findings" || selectedId.startsWith("findings-")) return <FindingsView snapshot={snapshot} selectedId={selectedId} title={selection.label} />;
  if (selectedId === "handoff") return <HandoffView snapshot={snapshot} />;
  if (selectedId === "evidence" || selectedId.startsWith("evidence-")) return <EvidenceView snapshot={snapshot} selectedId={selectedId} selection={selection} />;
  return <PacketOverview snapshot={snapshot} liveDocuments={liveDocuments} activity={activity} onSelect={onSelect} packetWork={packetWork} />;
}

function PacketOverview({ snapshot, liveDocuments, activity, onSelect, packetWork }: { snapshot: Snapshot; liveDocuments: LiveDocuments | null; activity: DevelopmentActivity | null; onSelect: (id: string) => void; packetWork: PacketWorkItem[] }) {
  const { t } = useI18n();
  const packet = snapshot.state.active_packet;
  const errors = snapshot.doctor.summary.errors;
  const warnings = snapshot.doctor.summary.warnings;
  const positive = errors === 0 && warnings === 0;
  return (
    <>
      <section className="product-banner" aria-label="SDAD Inspector product banner">
        <img
          src="/sdad-inspector-banner.png"
          alt="SDAD Inspector — Read-Only Control Plane for SPEC-Directed AI Development"
        />
      </section>
      <section className="packet-section" aria-labelledby="active-packet-heading">
        <p className="section-kicker">{t("activePacket")}</p>
        <div className="packet-heading-row">
          <h1 id="active-packet-heading">{packet?.id ?? t("noActivePacket")}</h1>
          <span className="status-badge lifecycle-status">
            <Info size={20} />
            {packet?.status ?? t("unavailable")}
          </span>
        </div>
        <h2>{t("objective")}</h2>
        <p className="objective">{packet?.objective ?? t("noPacketObjective")}</p>
      </section>

      <PacketEvidencePanel snapshot={snapshot} documents={liveDocuments} activity={activity} work={packetWork} />

      <section className="overview-section doctor-summary" aria-labelledby="doctor-summary-heading">
        <h2 id="doctor-summary-heading">{t("doctorSummary")}</h2>
        <p className={`doctor-counts ${positive ? "success" : "attention"}`}>
          <strong>{t(errors === 1 ? "errorCountOne" : "errorCountMany", { count: errors })}</strong>
          <span>·</span>
          <strong>{t(warnings === 1 ? "warningCountOne" : "warningCountMany", { count: warnings })}</strong>
        </p>
        <p>{snapshot.doctor.diagnostic_error?.message ?? (positive ? t("allValidationPresent") : t("reviewFindingsBeforeRelying"))}</p>
        {snapshot.doctor.findings.length > 0 && (
          <ul className="finding-list" aria-label={t("doctorFindings")}>
            {snapshot.doctor.findings.map((finding) => (
              <li key={`${finding.id}-${finding.path}-${finding.line ?? 0}`}>
                <WarningCircle size={18} />
                <div><strong>{finding.id}</strong><span>{finding.message}</span><code>{finding.path}{finding.line ? `:${finding.line}` : ""}</code></div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="overview-section" aria-labelledby="relationships-heading">
        <h2 id="relationships-heading">{t("relationships")}</h2>
        <div className="relationship-list">
          {snapshot.relationships.filter((relationship) => relationship.kind !== "handoff_to_packet" || relationship.from).map((relationship) => {
            const target = relationshipSelectionId(snapshot, relationship.from);
            return (
              <div className="relationship-row" key={relationship.kind}>
                <span>{relationshipLabel(relationship.kind, t)}</span>
                {relationship.kind === "active_spec_to_packet" ? <FileText size={18} /> : <Cube size={18} />}
                {target ? <button className="relationship-path" onClick={() => onSelect(target)} title={t("clickToRead")}><code>{relationship.from}</code></button> : <code>{relationship.from ?? t("notDeclared")}</code>}
                <span className={`relationship-status ${relationship.status}`}>{relationship.status.replaceAll("_", " ")}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section className="overview-section validation-section" aria-labelledby="validation-heading">
        <div className="section-heading-row">
          <h2 id="validation-heading">{t("declaredValidationCommands")}</h2>
          <span className="not-executed">{t("presentedNotExecuted")}</span>
        </div>
        {snapshot.state.validation.length ? (
          <ol className="command-list">
            {snapshot.state.validation.map((validation, index) => (
              <li key={`${validation.command}-${index}`}>
                <code>{validation.command}</code>
                <span>{validation.proves}</span>
              </li>
            ))}
          </ol>
        ) : <p className="empty-copy">{t("noValidationCommands")}</p>}
        <div className="info-note"><Info size={20} /><p>{t("validationEvidenceNote")}</p></div>
      </section>
    </>
  );
}

export function Overview({ snapshot, selectedId, selection, busy, progress, onSelect, liveDocuments, activity, packetWork, rule5 }: Props) {
  const { t } = useI18n();
  const overviewActive = selectedId === "overview" || selectedId === "packet";
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollPositions = useRef(new Map<string, number>());
  useLayoutEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollPositions.current.get(selectedId) ?? 0;
  }, [selectedId, snapshot.inspection_id, liveDocuments?.read_at, activity?.scanned_at]);
  return (
    <main className="overview-pane" id="overview" aria-label={t("workspaceView")}>
      <div className="pane-tabs overview-tabs" role="tablist" aria-label={t("workspaceView")}>
        <button className={overviewActive ? "active" : ""} role="tab" aria-selected={overviewActive} aria-controls="workspace-panel" onClick={() => onSelect("overview")}>{t("overview")}</button>
        {!overviewActive && <button className="active context-tab" role="tab" aria-selected="true" aria-controls="workspace-panel">{selection.label}</button>}
      </div>
      <InspectionProgress active={busy} progress={progress} />
      {snapshot.inspection_status === "stale" && <div className="stale-banner" role="status"><WarningCircle size={18} /> {t("staleInspection")}</div>}
      <div className="overview-scroll" id="workspace-panel" role="tabpanel" ref={scrollRef} onScroll={(event) => scrollPositions.current.set(selectedId, event.currentTarget.scrollTop)}>
        {overviewActive ? <PacketOverview snapshot={snapshot} liveDocuments={liveDocuments} activity={activity} onSelect={onSelect} packetWork={packetWork} /> : <ContextView snapshot={snapshot} selectedId={selectedId} selection={selection} liveDocuments={liveDocuments} activity={activity} onSelect={onSelect} packetWork={packetWork} rule5={rule5} />}
      </div>
    </main>
  );
}
