import { useState } from "react";
import {
  CaretDown,
  CaretRight,
  Copy,
  Eye,
  FileText,
  Lock,
  X,
} from "@phosphor-icons/react";
import { type Translate, useI18n } from "../i18n";
import type { FieldSelection, Snapshot } from "../types";

interface Props {
  snapshot: Snapshot;
  selection: FieldSelection;
  onReveal: (path: string) => void;
  onCopy: (value: string, label: string) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

function gateLabel(gate: string, t: Translate): string {
  if (gate === "release") return t("gateRelease");
  if (gate === "signing") return t("gateSigning");
  if (gate === "publishing") return t("gatePublishing");
  if (gate === "auto-fix/write") return t("gateAutoFixWrite");
  return gate;
}

export function InspectorPane({ snapshot, selection, onReveal, onCopy, mobileOpen, onCloseMobile }: Props) {
  const { t } = useI18n();
  const [tab, setTab] = useState<"inspector" | "raw">("inspector");
  const [actionsExpanded, setActionsExpanded] = useState(true);
  const gates = snapshot.state.owner_gates;
  return (
    <aside className={`inspector-pane ${mobileOpen ? "mobile-open" : ""}`} aria-label={t("inspectorDetails")}>
      <div className="pane-tabs inspector-tabs" role="tablist" aria-label={t("inspectorView")}>
        <button className={tab === "inspector" ? "active" : ""} role="tab" aria-selected={tab === "inspector"} onClick={() => setTab("inspector")}>{t("inspector")}</button>
        <button className={tab === "raw" ? "active" : ""} role="tab" aria-selected={tab === "raw"} onClick={() => setTab("raw")}>{t("rawJson")}</button>
        <button className="mobile-close" onClick={onCloseMobile} aria-label={t("closeInspector")}><X size={18} /></button>
      </div>
      {tab === "raw" ? (
        <div className="raw-panel">
          <div className="raw-toolbar">
            <span>{t("snapshotSchema", { version: snapshot.snapshot_schema_version })}</span>
            <button onClick={() => onCopy(JSON.stringify(snapshot, null, 2), t("labelSnapshotJson"))}><Copy size={16} /> {t("copyJson")}</button>
          </div>
          <pre tabIndex={0}>{JSON.stringify(snapshot, null, 2)}</pre>
        </div>
      ) : (
        <div className="inspector-scroll">
          <section className="field-details" aria-labelledby="field-details-heading">
            <h2 id="field-details-heading">{t("fieldDetails")}</h2>
            <dl>
              <div><dt>{t("authority")}</dt><dd>{selection.authority}</dd></div>
              <div><dt>{t("observedValue")}</dt><dd className="observed-value">{selection.observed}</dd></div>
              <div><dt>{t("sourcePath")}</dt><dd><button className="inline-copy" onClick={() => onCopy(selection.sourcePath, t("labelSourcePath"))}><Copy size={15} /><code>{selection.sourcePath}</code></button></dd></div>
              <div><dt>{t("freshness")}</dt><dd>{selection.freshness}</dd></div>
              <div><dt>{t("relatedFinding")}</dt><dd>{selection.relatedFinding}</dd></div>
              <div><dt>{t("remediation")}</dt><dd>{selection.remediation}</dd></div>
            </dl>
          </section>

          <section className="owner-gates" aria-labelledby="owner-gates-heading">
            <div className="gate-heading">
              <h2 id="owner-gates-heading">{t("declaredOwnerGates")} <span>{t("readOnlyParenthetical")}</span></h2>
              <Lock size={18} />
            </div>
            {gates.length ? (
              <ul>
                {gates.map((gate) => {
                  const label = gateLabel(gate, t);
                  const status = t("approvalUnobserved");
                  return <li key={gate}><span className="gate-square" /><span className="gate-label" title={label}>{label}</span><strong className="gate-status" title={status}>{status}</strong></li>;
                })}
              </ul>
            ) : <p className="empty-copy">{t("noOwnerGate")}</p>}
            <p className="gate-note">{t("ownerGateNote")}</p>
          </section>

          <section className="safe-actions" aria-labelledby="safe-actions-heading">
            <button className="actions-heading" onClick={() => setActionsExpanded((value) => !value)} aria-expanded={actionsExpanded}>
              {actionsExpanded ? <CaretDown size={16} /> : <CaretRight size={16} />}
              <span id="safe-actions-heading">{t("safeActions")}</span>
            </button>
            {actionsExpanded && (
              <div className="action-rows">
                <button onClick={() => onReveal(selection.revealPath)}><Eye size={18} /><span>{t("revealFile")}</span><code>{selection.revealPath}</code></button>
                <button onClick={() => onCopy(selection.sourcePath, t("labelPath"))}><Copy size={18} /><span>{t("copyPath")}</span><code>{selection.sourcePath}</code></button>
                <button onClick={() => setTab("raw")}><FileText size={18} /><span>{t("openRawJson")}</span><em>{t("preservedEvidence")}</em></button>
              </div>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}
