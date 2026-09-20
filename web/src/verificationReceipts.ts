export type IdentityMatch = "matched" | "changed" | "unknown";
export interface VerificationReceipt {
  schema: "sdad.verification-receipt";
  version: 1;
  id: string;
  packet: string;
  requirement: string;
  scope: string;
  cwd: string;
  command: { argv: string[]; python_version: string; platform: string };
  started_at: string;
  ended_at: string;
  outcome: "passed" | "failed" | "timeout" | "start_failed" | "interrupted";
  exit_code: number | null;
  source_stability: "stable" | "changed" | "unknown";
  sources: Array<{ path: string; before: { sha256: string; size: number } | null; after: { sha256: string; size: number } | null; error: string | null }>;
  log: { path: string; sha256: string; bytes: number; total_bytes: number; truncated: boolean; complete: boolean };
  limits: string[];
}
export interface ReceiptObservation {
  path: string;
  receipt: VerificationReceipt | null;
  source_match: IdentityMatch;
  log_match: IdentityMatch;
  sources: Array<{ path: string; match: IdentityMatch; reason: string | null }>;
  error: string | null;
}
export interface VerificationReceipts {
  project_root: string;
  packet: string | null;
  read_at: string;
  receipts: ReceiptObservation[];
  truncated: boolean;
}

export interface VerificationReceiptList {
  version: 1;
  project_root: string;
  packet: string | null;
  read_at: string;
  revision: string;
  offset: number;
  total: number;
  next_offset: number | null;
  paths: string[];
}

export interface VerificationReceiptInspection {
  version: 1;
  project_root: string;
  packet: string | null;
  read_at: string;
  revision: string;
  observation: ReceiptObservation;
}
