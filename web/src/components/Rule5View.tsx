import { useEffect, useMemo, useState } from "react";
import { CheckCircle, DownloadSimple, FileText, FunnelSimple, Info, WarningCircle } from "@phosphor-icons/react";
import { ApiError, exportRule5Candidate, previewRule5Candidate } from "../api";
import { useI18n } from "../i18n";
import type { Rule5Candidate, Rule5Candidates, Rule5Preview } from "../types";
import { MarkdownViewer } from "./MarkdownViewer";

const REQUIRED: Array<keyof Rule5Candidate> = [
  "observed_failure",
  "root_cause",
  "operational_rule",
  "enforcement",
  "regression_evidence",
  "review_condition",
];

function isComplete(candidate: Rule5Candidate | null): boolean {
  return Boolean(candidate && REQUIRED.every((field) => String(candidate[field]).trim()));
}

export function Rule5View({ data }: { data: Rule5Candidates | null }) {
  const { t } = useI18n();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Rule5Candidate | null>(null);
  const [preview, setPreview] = useState<Rule5Preview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const selected = data?.candidates.find((candidate) => candidate.candidate_id === selectedId)
      ?? data?.candidates.find((candidate) => candidate.complete)
      ?? data?.candidates[0]
      ?? null;
    setSelectedId(selected?.candidate_id ?? null);
    setDraft(selected ? { ...selected } : null);
    setPreview(null); setConfirmed(false); setMessage(null); setError(null);
  }, [data?.source_sha256]);

  const missing = useMemo(() => draft ? REQUIRED.filter((field) => !String(draft[field]).trim()) : REQUIRED, [draft]);

  function select(candidate: Rule5Candidate) {
    setSelectedId(candidate.candidate_id); setDraft({ ...candidate }); setPreview(null); setConfirmed(false); setMessage(null); setError(null);
  }

  function update(field: keyof Rule5Candidate, value: string) {
    setDraft((current) => current ? { ...current, [field]: value } : current);
    setPreview(null); setConfirmed(false); setMessage(null); setError(null);
  }

  async function extract() {
    if (!draft || !isComplete(draft)) return;
    setBusy(true); setError(null); setMessage(null); setConfirmed(false);
    try { setPreview(await previewRule5Candidate(draft)); }
    catch (reason) { setError(reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("rule5PreviewFailed")); }
    finally { setBusy(false); }
  }

  async function save() {
    if (!draft || !preview || !confirmed) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await exportRule5Candidate(draft, preview.sha256);
      setMessage(result.cancelled ? t("rule5SaveCancelled") : t("rule5SavedTo", { path: result.path ?? "" }));
      if (result.saved) setConfirmed(false);
    } catch (reason) { setError(reason instanceof ApiError ? `${reason.code}: ${reason.message}` : t("rule5SaveFailed")); }
    finally { setBusy(false); }
  }

  return (
    <div className="context-view rule5-view">
      <header className="rule5-header">
        <span className="context-icon"><FunnelSimple size={25} /></span>
        <div><p className="section-kicker">Rule 5</p><h1>{t("rule5Title")}</h1><p>{t("rule5Description")}</p></div>
      </header>
      <div className="rule5-caveat"><Info size={19} /><p>{t("rule5CandidateCaveat")}</p></div>
      {!data ? <div className="document-empty">{t("inspectingRepository")}</div> : !data.candidates.length ? <div className="document-empty">{t("rule5NoCandidates")}</div> : (
        <div className="rule5-layout">
          <aside className="rule5-candidates" aria-label={t("rule5Candidates")}>
            <div><strong>{t("rule5Candidates")}</strong><span>{data.candidates.length}</span></div>
            <ul>{data.candidates.map((candidate) => <li key={candidate.candidate_id}><button className={candidate.candidate_id === selectedId ? "active" : ""} onClick={() => select(candidate)}><FileText size={18} /><span><strong>{candidate.finding_id}</strong><small>{candidate.observed_failure}</small></span>{candidate.complete ? <CheckCircle size={17} weight="fill" /> : <WarningCircle size={17} />}</button></li>)}</ul>
          </aside>
          {draft && <section className="rule5-editor" aria-label={t("rule5Editor")}>
            <div className="rule5-editor-heading"><div><p>{t("rule5Source")}</p><code>{draft.source_path} · {draft.finding_id}</code></div><span className={missing.length ? "incomplete" : "complete"}>{missing.length ? t("rule5MissingFields", { count: missing.length }) : t("rule5ReadyToExtract")}</span></div>
            <div className="rule5-fields">
              <label><span>{t("rule5ObservedFailure")}</span><textarea value={draft.observed_failure} onChange={(event) => update("observed_failure", event.target.value)} /></label>
              <label><span>{t("rule5RootCause")}</span><textarea value={draft.root_cause} onChange={(event) => update("root_cause", event.target.value)} /></label>
              <label className="wide"><span>{t("rule5OperationalRule")}</span><textarea value={draft.operational_rule} onChange={(event) => update("operational_rule", event.target.value)} /></label>
              <label><span>{t("rule5Enforcement")}</span><textarea value={draft.enforcement} onChange={(event) => update("enforcement", event.target.value)} /></label>
              <label><span>{t("rule5RegressionEvidence")}</span><textarea value={draft.regression_evidence} onChange={(event) => update("regression_evidence", event.target.value)} /></label>
              <label className="wide"><span>{t("rule5ReviewCondition")}</span><textarea value={draft.review_condition} onChange={(event) => update("review_condition", event.target.value)} /></label>
            </div>
            <details className="rule5-advanced"><summary>{t("rule5AdvancedFields")}</summary><div className="rule5-fields"><label><span>{t("rule5Trigger")}</span><textarea value={draft.trigger} onChange={(event) => update("trigger", event.target.value)} /></label><label><span>{t("rule5NonTrigger")}</span><textarea value={draft.non_trigger} onChange={(event) => update("non_trigger", event.target.value)} /></label><label><span>{t("rule5Exceptions")}</span><textarea value={draft.exceptions} onChange={(event) => update("exceptions", event.target.value)} /></label><label><span>{t("rule5Limits")}</span><textarea value={draft.limits} onChange={(event) => update("limits", event.target.value)} /></label></div></details>
            <div className="rule5-actions"><button className="extract-rule" disabled={busy || missing.length > 0} onClick={() => void extract()}><FunnelSimple size={18} />{t("rule5Extract")}</button>{missing.length > 0 && <small>{t("rule5CompleteFieldsFirst")}</small>}</div>
            {preview && <section className="rule5-preview" aria-label={t("rule5Preview")}><div className="rule5-preview-heading"><div><strong>{t("rule5Preview")}</strong><code>SHA-256 {preview.sha256}</code></div><span>{preview.suggested_filename}</span></div><MarkdownViewer document={{ path: preview.suggested_filename, exists: true, roles: ["rule5-preview"], content: preview.markdown, error: null }} /><label className="rule5-confirm"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>{t("rule5ConfirmPreview")}</span></label><button className="save-rule" disabled={busy || !confirmed} onClick={() => void save()}><DownloadSimple size={19} />{t("rule5SaveLocal")}</button></section>}
            {error && <p className="rule5-result error" role="alert">{error}</p>}
            {message && <p className="rule5-result" role="status">{message}</p>}
          </section>}
        </div>
      )}
    </div>
  );
}
