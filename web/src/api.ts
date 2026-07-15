import type { DevelopmentActivity, InspectionProgress, LiveDocuments, ProductUpdateStatus, RecentProject, Rule5Candidate, Rule5Candidates, Rule5ExportResult, Rule5Preview, Snapshot } from "./types";

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

export function getInspectionProgress(): Promise<InspectionProgress> {
  return request<InspectionProgress>("/api/progress");
}

export function getLiveDocuments(): Promise<LiveDocuments> {
  return request<LiveDocuments>("/api/documents");
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
