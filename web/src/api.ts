import type { DevelopmentActivity, DocumentPage, InspectionProgress, LiveDocuments, ProductUpdateStatus, RecentProject, Rule5Candidate, Rule5Candidates, Rule5ExportResult, Rule5Preview, Snapshot } from "./types";

export interface UiPreferences {
  schema_version: number;
  theme: "light" | "dark" | null;
  locale: "en" | "ko" | "ja" | "zh-CN" | null;
  scale: number | null;
}

function sessionToken(): string {
  return document.querySelector<HTMLMetaElement>('meta[name="sdad-session"]')?.content ?? "";
}

export class ApiError extends Error {
  code: string;

  constructor(message: string, code = "request_failed") {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("X-SDAD-Session", sessionToken());
  if (init?.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers, credentials: "same-origin" });
  const payload = (await response.json()) as T & {
    error?: { code?: string; message?: string };
  };
  if (!response.ok) {
    throw new ApiError(
      payload.error?.message ?? "The local Inspector request failed.",
      payload.error?.code,
    );
  }
  return payload;
}

export function getSnapshot(): Promise<Snapshot> {
  return request<Snapshot>("/api/snapshot");
}

export function resumeComparisonAction(projectRoot: string, inspectionId: string, action: "read" | "enable" | "observe" | "replace" | "clear" | "clear_all"): Promise<import("./resumeComparison").ResumeStore & { retained_projects: number }> {
  return request("/api/resume-comparison", { method: "POST", body: JSON.stringify({ project_root: projectRoot, inspection_id: inspectionId, action }) });
}

export function getInspectionProgress(): Promise<InspectionProgress> {
  return request<InspectionProgress>("/api/progress");
}

export function getLiveDocuments(): Promise<LiveDocuments> {
  return request<LiveDocuments>("/api/documents");
}

export function getDocumentPage(projectRoot: string, path: string, start = 1, count = 100, expectedSha256?: string): Promise<DocumentPage> {
  return request<DocumentPage>("/api/documents/page", {
    method: "POST",
    body: JSON.stringify({ project_root: projectRoot, path, start, lines: count, expected_sha256: expectedSha256 }),
  });
}

export function getVerificationReceipts(project_root: string): Promise<import("./verificationReceipts").VerificationReceipts> {
  return request("/api/verification-receipts", { method: "POST", body: JSON.stringify({ project_root }) });
}

export function getVerificationReceiptList(project_root: string, offset = 0, revision?: string): Promise<import("./verificationReceipts").VerificationReceiptList> {
  return request("/api/verification-receipt-list", { method: "POST", body: JSON.stringify({ project_root, offset, revision }) });
}

export function inspectVerificationReceipt(project_root: string, path: string, revision: string): Promise<import("./verificationReceipts").VerificationReceiptInspection> {
  return request("/api/verification-receipt-inspect", { method: "POST", body: JSON.stringify({ project_root, path, revision }) });
}

export function getDevelopmentActivity(): Promise<DevelopmentActivity> {
  return request<DevelopmentActivity>("/api/activity");
}

interface RecentProjectsPayload {
  schema_version: number;
  recent_projects: Array<{ path: string; name: string; opened_at: string }>;
}

function mapRecentProjects(payload: RecentProjectsPayload): RecentProject[] {
  return payload.recent_projects.map((project) => ({
    path: project.path,
    name: project.name,
    openedAt: project.opened_at,
  }));
}

export async function getRecentProjects(): Promise<RecentProject[]> {
  return mapRecentProjects(await request<RecentProjectsPayload>("/api/recent-projects"));
}

export async function clearRecentProjectHistory(): Promise<RecentProject[]> {
  return mapRecentProjects(await request<RecentProjectsPayload>("/api/recent-projects/clear", {
    method: "POST",
    body: "{}",
  }));
}

export function getRule5Candidates(): Promise<Rule5Candidates> {
  return request<Rule5Candidates>("/api/rule5-candidates");
}

export function previewRule5Candidate(candidate: Rule5Candidate): Promise<Rule5Preview> {
  return request<Rule5Preview>("/api/rule5/preview", {
    method: "POST",
    body: JSON.stringify(candidate),
  });
}

export function exportRule5Candidate(candidate: Rule5Candidate, previewSha256: string): Promise<Rule5ExportResult> {
  return request<Rule5ExportResult>("/api/rule5/export", {
    method: "POST",
    body: JSON.stringify({ ...candidate, confirmed: true, preview_sha256: previewSha256 }),
  });
}

export function rescanProject(): Promise<Snapshot> {
  return request<Snapshot>("/api/rescan", { method: "POST", body: "{}" });
}

export function openProject(projectRoot: string): Promise<Snapshot> {
  return request<Snapshot>("/api/project", {
    method: "POST",
    body: JSON.stringify({ project_root: projectRoot }),
  });
}

export function pickProjectDirectory(initialPath: string): Promise<{ selected: boolean; project_root: string | null }> {
  return request<{ selected: boolean; project_root: string | null }>("/api/project-picker", {
    method: "POST",
    body: JSON.stringify({ initial_path: initialPath }),
  });
}

export function pasteProjectPath(): Promise<{ project_root: string }> {
  return request<{ project_root: string }>("/api/clipboard/project-path", {
    method: "POST",
    body: "{}",
  });
}

export function revealPath(relativePath: string): Promise<{ revealed: boolean }> {
  return request<{ revealed: boolean }>("/api/reveal", {
    method: "POST",
    body: JSON.stringify({ relative_path: relativePath }),
  });
}

export function getProductUpdateStatus(): Promise<ProductUpdateStatus> {
  return request<ProductUpdateStatus>("/api/update");
}

export function checkProductUpdate(force = false): Promise<ProductUpdateStatus> {
  return request<ProductUpdateStatus>("/api/update/check", {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

export function applyProductUpdate(): Promise<ProductUpdateStatus> {
  return request<ProductUpdateStatus>("/api/update/apply", {
    method: "POST",
    body: "{}",
  });
}

export function acknowledgeProductUpdate(): Promise<ProductUpdateStatus> {
  return request<ProductUpdateStatus>("/api/update/acknowledge", {
    method: "POST",
    body: "{}",
  });
}

export function updateUiPreferences(preferences: Partial<Pick<UiPreferences, "theme" | "locale" | "scale">>): Promise<UiPreferences> {
  return request<UiPreferences>("/api/preferences", {
    method: "POST",
    body: JSON.stringify(preferences),
  });
}

export function openRepository(): Promise<{ opened: boolean; url: string }> {
  return request<{ opened: boolean; url: string }>("/api/open-repository", {
    method: "POST",
    body: "{}",
  });
}

export interface CorrectionUsage {active_count: number; active_limit: number; active_bytes: number; byte_limit: number; archived_count: number; project_archived_count: number}
export interface CorrectionHistory {schema_version: number; project_root: string; drafts: import("./interactions").Correction[]; usage?: CorrectionUsage; has_more?: boolean; offset?: number; archived?: boolean; leaf_id?: string | null}
export function getCorrections(): Promise<CorrectionHistory> {
  return request("/api/corrections");
}
export function saveCorrection(draft: import("./interactions").Correction): Promise<import("./interactions").Correction> {
  return request("/api/corrections", {method: "POST", body: JSON.stringify(draft)});
}

export function getCorrectionHistory(project_root: string, archived: boolean, offset = 0, packet?: string, request_id?: string): Promise<CorrectionHistory> {
  return request("/api/corrections/history", {method: "POST", body: JSON.stringify({project_root, archived, offset, packet, request_id})});
}
export function manageCorrection(project_root: string, operation: 'archive' | 'restore', draft: import("./interactions").Correction): Promise<import("./interactions").Correction> {
  return request(`/api/corrections/${operation}`, {method: "POST", body: JSON.stringify({project_root, draft, confirmed: true})});
}
export function importCorrection(project_root: string, bundle: unknown): Promise<import("./interactions").Correction> {
  return request("/api/corrections/import", {method: "POST", body: JSON.stringify({project_root, bundle})});
}
