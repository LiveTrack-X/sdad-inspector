import type { Translate } from "./i18n";
import type { PacketWorkItem } from "./packetWork";
import type { FieldSelection, Snapshot } from "./types";

function inspected(snapshot: Snapshot): string {
  return snapshot.inspected_at;
}

export function documentPathForSelection(snapshot: Snapshot, id: string): string | null {
  if (id === "spec") return snapshot.state.active_spec?.path ?? null;
  if (id === "todo") return snapshot.protocol.todo_path;
  if (id.startsWith("doc:")) {
    try { return decodeURIComponent(id.slice(4)); } catch { return null; }
  }
  return null;
}

export function documentSelectionId(snapshot: Snapshot, path: string): string {
  if (path === snapshot.state.active_spec?.path) return "spec";
  if (path === snapshot.protocol.todo_path) return "todo";
  return `doc:${encodeURIComponent(path)}`;
}

export function selectionFor(snapshot: Snapshot, id: string, t: Translate, packetWork: PacketWorkItem[] = []): FieldSelection {
  const packet = snapshot.state.active_packet;
  const spec = snapshot.state.active_spec;
  const handoff = snapshot.state.current_handoff;
  const statePath = snapshot.protocol.state_path;
  const todoPath = snapshot.protocol.todo_path;
  const findingsPath = snapshot.protocol.findings_path;
  const base = {
    id,
    freshness: inspected(snapshot),
    relatedFinding: t("none"),
    remediation: t("noRemediationDeclared"),
  };
  const documentPath = documentPathForSelection(snapshot, id);
  if (id.startsWith("doc:")) {
    return {
      ...base,
      label: documentPath ?? t("documents"),
      authority: `${statePath}#routed_docs`,
      observed: t("liveDocument"),
      sourcePath: documentPath ?? statePath,
      remediation: t("clickToRead"),
      revealPath: documentPath ?? statePath,
    };
  }
  switch (id) {
    case "overview":
      return {
        ...base,
        label: t("overview"),
        authority: `${statePath}#active_packet`,
        observed: packet?.status ?? t("notDeclared"),
        sourcePath: statePath,
        remediation: packet ? t("statusDeclared") : t("declareActivePacket"),
        revealPath: statePath,
      };
    case "development":
      return {
        ...base,
        label: t("developmentFlow"),
        authority: t("liveRepositorySignal"),
        observed: t("observedChanges"),
        sourcePath: ".git",
        remediation: t("timestampBasis"),
        revealPath: ".",
      };
    case "rule5":
      return {
        ...base,
        label: t("rule5Title"),
        authority: `${findingsPath}#Active Findings`,
        observed: t("rule5CandidateCaveat"),
        sourcePath: findingsPath,
        remediation: t("rule5Description"),
        revealPath: findingsPath,
      };
    case "state":
      return {
        ...base,
        label: t("state"),
        authority: statePath,
        observed: packet?.status ?? t("unavailable"),
        sourcePath: `${statePath}#active_packet.status`,
        remediation: packet ? t("stateReadSuccess") : t("createReadableState"),
        revealPath: statePath,
      };
    case "spec":
      return {
        ...base,
        label: t("activeSpec"),
        authority: `${statePath}#active_spec`,
        observed: spec?.path ?? t("notDeclared"),
        sourcePath: spec?.path ?? statePath,
        remediation: spec?.exists ? t("declaredSpecExists") : t("restoreDeclaredSpec"),
        revealPath: spec?.path ?? statePath,
      };
    case "todo":
      const packetOpen = packetWork.filter((item) => !item.completed).length;
      return {
        ...base,
        label: t("activeTodo"),
        authority: `${todoPath}#Active Work`,
        observed: t(packetOpen === 1 ? "openItemOne" : "openItemMany", { count: packetOpen }),
        sourcePath: todoPath,
        remediation: t("reviewOpenWork"),
        revealPath: todoPath,
      };
    case "findings-errors":
    case "findings-warnings":
    case "findings-notes": {
      const severity = id.endsWith("errors") ? "error" : id.endsWith("warnings") ? "warning" : "note";
      const severityLabel = severity === "error" ? t("errors") : severity === "warning" ? t("warnings") : t("notes");
      const count = snapshot.doctor.findings.filter((finding) => finding.severity === severity).length;
      const first = snapshot.doctor.findings.find((finding) => finding.severity === severity);
      return {
        ...base,
        label: severity === "error" ? t("doctorErrors") : severity === "warning" ? t("doctorWarnings") : t("notes"),
        authority: t("doctorFindingAuthority"),
        observed: t(count === 1 ? "severityCountOne" : "severityCountMany", { count, severity: severityLabel }),
        sourcePath: first?.path ?? t("doctorReportJson"),
        relatedFinding: first?.id ?? t("none"),
        remediation: first?.remediation ?? t("noSeverityRemediation", { severity: severityLabel }),
        revealPath: first?.path ?? ".",
      };
    }
    case "findings":
      return {
        ...base,
        label: t("reviewFindings"),
        authority: t("doctorFindingAuthority"),
        observed: t("findingTotal", { count: snapshot.doctor.findings.length }),
        sourcePath: t("inMemoryDoctorJson"),
        relatedFinding: snapshot.doctor.findings[0]?.id ?? t("none"),
        remediation: snapshot.doctor.findings[0]?.remediation ?? t("noFindingsForSelection"),
        revealPath: snapshot.doctor.findings[0]?.path ?? ".",
      };
    case "handoff":
      return {
        ...base,
        label: t("currentHandoff"),
        authority: `${statePath}#current_handoff`,
        observed: handoff?.declared ? (handoff.exists ? t("declaredPresent") : t("declaredMissing")) : t("notDeclared"),
        sourcePath: handoff?.path ?? statePath,
        remediation: handoff?.declared && !handoff.exists ? t("restoreOrClearHandoff") : t("noHandoffAction"),
        revealPath: handoff?.path ?? statePath,
      };
    case "evidence-doctor":
      return {
        ...base,
        label: t("doctorReport"),
        authority: `${snapshot.protocol.engine_display_name} Doctor`,
        observed: t("exitAndSchema", { exit: snapshot.doctor.exit_code, schema: snapshot.contracts.report_schema_version }),
        sourcePath: t("inMemoryDoctorJson"),
        remediation: t("rawEvidencePreserved"),
        revealPath: ".",
      };
    case "evidence":
      return {
        ...base,
        label: t("evidenceIndex"),
        authority: t("normalizedSnapshot"),
        observed: t("evidenceSourceCount", { count: Object.keys(snapshot.evidence.files).length + 2 }),
        sourcePath: t("inMemorySnapshot"),
        remediation: t("readOnlyEvidenceNote"),
        revealPath: ".",
      };
    case "evidence-state":
      return {
        ...base,
        label: t("stateEvidence"),
        authority: t("repositoryControlState"),
        observed: snapshot.state.available ? t("stateSchemaValue", { schema: snapshot.state.schema_version ?? "—" }) : t("missing"),
        sourcePath: statePath,
        remediation: snapshot.state.available ? t("boundedStateRead") : t("createReadableStateShort"),
        revealPath: statePath,
      };
    case "evidence-spec":
      return { ...selectionFor(snapshot, "spec", t, packetWork), id };
    case "evidence-todo":
      return { ...selectionFor(snapshot, "todo", t, packetWork), id };
    case "evidence-findings":
      return {
        ...base,
        label: t("reviewFindingsEvidence"),
        authority: `${findingsPath}#Active Findings`,
        observed: t("openCount", { count: snapshot.state.ledger.review_findings_open }),
        sourcePath: findingsPath,
        remediation: t("reviewPacketFindings"),
        revealPath: findingsPath,
      };
    case "evidence-handoff":
      return { ...selectionFor(snapshot, "handoff", t, packetWork), id };
    case "evidence-snapshot":
      return {
        ...base,
        label: t("normalizedSnapshot"),
        authority: `SDAD Inspector ${snapshot.inspector_version}`,
        observed: t("snapshotSchemaValue", { schema: snapshot.snapshot_schema_version }),
        sourcePath: t("inMemorySnapshot"),
        remediation: t("replaceSnapshot"),
        revealPath: ".",
      };
    case "packet":
    default:
      return {
        ...base,
        id: "packet",
        label: t("activePacket"),
        authority: `${statePath}#active_packet`,
        observed: packet?.status ?? t("notDeclared"),
        sourcePath: `${statePath}#active_packet.status`,
        remediation: packet ? t("statusDeclared") : t("declareActivePacket"),
        revealPath: statePath,
      };
  }
}
