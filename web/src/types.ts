export type Severity = "error" | "warning" | "note" | string;

export interface Finding {
  id: string;
  severity: Severity;
  path: string;
  line: number | null;
  message: string;
  evidence: string;
  remediation: string;
}

export interface ValidationDeclaration {
  command: string;
  proves: string;
  executed: false;
}

export interface Snapshot {
  snapshot_schema_version: number;
  inspector_version: string;
  inspection_id: string;
  inspected_at: string;
  inspection_status: "completed" | "diagnostic" | "stale" | string;
  read_only: true;
  project: {
    root: string;
    name: string;
    identity: string;
  };
  protocol: {
    adapter_id: string;
    protocol_name: string;
    engine_name: string;
    engine_display_name: string;
    doctor_entrypoint: string;
    state_path: string;
    todo_path: string;
    findings_path: string;
    supported_engine_versions: string[];
    supported_report_schemas: number[];
    supported_state_schemas: number[];
    normalized_control_loop: string[];
    capabilities: string[];
  };
  engine: {
    checkout: string;
    doctor_version: string;
    release_tag: string;
    revision: string;
    source: string | null;
    trust: string;
    clean: boolean;
  };
  contracts: {
    doctor_version: string;
    report_schema_version: number;
    state_schema_version: number | null;
    snapshot_schema_version: number;
  };
  doctor: {
    report_schema_version: number;
    doctor_version: string;
    state_schema_version: number | null;
    root: string | null;
    strict: boolean;
    summary: { errors: number; warnings: number };
    checks: { run: string[]; skipped: string[] };
    findings: Finding[];
    diagnostic_error: { kind: string; message: string } | null;
    exit_code: number;
    completed: boolean;
    argv_shape: string[];
    stderr_present: boolean;
  };
  state: {
    available: boolean;
    schema_version: number | null;
    updated?: string | null;
    scale?: string | null;
    execution_scope?: string | null;
    legacy_controls?: { intensity: string | null; autonomy: number | null };
    active_spec: { path: string; exists: boolean } | null;
    active_packet: { id: string; objective: string; status: string } | null;
    validation_for: string | null;
    validation: ValidationDeclaration[];
    owner_gates: string[];
    routed_docs: string[];
    current_handoff: { path: string | null; declared: boolean; exists: boolean } | null;
    ledger: {
      todo_open: number;
      review_findings_open: number;
      review_findings_by_severity: Record<string, number>;
    };
  };
  relationships: Array<{
    kind: string;
    from: string | null;
    to: string | null;
    status: string;
  }>;
  integrity: {
    watched_control_paths: string[];
    control_files_unchanged_during_inspection: boolean;
  };
  evidence: {
    files: Record<string, Record<string, unknown>>;
    doctor_report: Record<string, unknown>;
    doctor_exit_code: number;
  };
  limitations: string[];
}

export interface FieldSelection {
  id: string;
  label: string;
  authority: string;
  observed: string;
  sourcePath: string;
  freshness: string;
  relatedFinding: string;
  remediation: string;
  revealPath: string;
}

export type InspectionStage = "prepare" | "doctor" | "controls" | "integrity" | "report";

export interface InspectionProgressEvent {
  stage: InspectionStage;
  source: string;
  event: string;
  at: string;
}

export interface InspectionProgress {
  operation_id: string | null;
  kind: "initial" | "rescan" | "open_project" | null;
  status: "idle" | "running" | "completed" | "failed";
  stage: InspectionStage;
  stage_index: number;
  stage_count: number;
  current_source: string | null;
  event: string;
  started_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  recent: InspectionProgressEvent[];
  error_code?: string;
}

export interface LiveDocument {
  path: string;
  exists: boolean;
  roles: string[];
  content: string | null;
  bytes?: number;
  modified_ns?: number;
  sha256?: string;
  error: { code: string; message: string } | null;
}

export interface LiveDocuments {
  project_root: string;
  read_at: string;
  documents: LiveDocument[];
  truncated: boolean;
}

export interface ActivityFile {
  path: string;
  previous_path: string | null;
  status: string;
  kind: string;
  modified_at: string | null;
}

export interface ActivityCommit {
  revision: string;
  short_revision: string;
  committed_at: string;
  subject: string;
}

export interface HandoffRecord {
  path: string;
  title: string;
  summary: string;
  modified_at: string;
  current: boolean;
}

export interface DevelopmentActivity {
  project_root: string;
  git_root: string | null;
  git_scope: string | null;
  available: boolean;
  worktree_status: "changed" | "clean" | "unavailable";
  scanned_at: string;
  duration_ms: number;
  changed_count: number;
  truncated: boolean;
  counts: Record<string, number>;
  files: ActivityFile[];
  commits: ActivityCommit[];
  handoffs: HandoffRecord[];
  error: { code: string; message: string } | null;
}

export interface RecentProject {
  path: string;
  name: string;
  openedAt: string;
}

export interface Rule5Candidate {
  candidate_id: string;
  finding_id: string;
  source_path: string;
  source_sha256: string;
  observed_failure: string;
  root_cause: string;
  operational_rule: string;
  trigger: string;
  non_trigger: string;
  exceptions: string;
  enforcement: string;
  regression_evidence: string;
  limits: string;
  review_condition: string;
  complete: boolean;
}

export interface Rule5Candidates {
  source_path: string;
  source_sha256: string;
  candidates: Rule5Candidate[];
}

export interface Rule5Preview {
  markdown: string;
  sha256: string;
  suggested_filename: string;
}

export interface Rule5ExportResult extends Rule5Preview {
  saved: boolean;
  cancelled: boolean;
  path: string | null;
}

export type RescanMode = "manual" | "auto";

export type ProductUpdateState =
  | "unsupported"
  | "idle"
  | "checking"
  | "up_to_date"
  | "downloading"
  | "ready"
  | "applying"
  | "updated"
  | "error";

export interface ProductUpdateStatus {
  supported: boolean;
  automatic: true;
  current_version: string;
  state: ProductUpdateState;
  available_version: string | null;
  release_url: string | null;
  downloaded_bytes: number;
  total_bytes: number;
  checked_at: string | null;
  message: string | null;
  error: string | null;
}
