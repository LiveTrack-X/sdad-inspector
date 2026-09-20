import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { I18nProvider } from "./i18n";
import { activityFixture, emptyResumeComparisonFixture, liveDocumentsFixture, rule5CandidatesFixture, snapshotFixture } from "./test/fixture";

vi.mock("./components/InteractionPanel", () => ({ InteractionPanel: () => null }));

describe("Doctor re-scan announcements", () => {
  it.each(["api", "transport"])("keeps previous evidence stale after a %s failure, then replaces it only after recovery", async (kind) => {
    let failed = false;
    const recovered = { ...snapshotFixture, inspection_id: "recovered-inspection", inspected_at: "2026-09-20T05:00:00Z" };
    vi.stubGlobal("fetch", vi.fn(async (input) => {
      const path = String(input);
      if (path === "/api/rescan" && !failed) {
        failed = true;
        if (kind === "transport") throw new TypeError("Local connection interrupted");
        return new Response(JSON.stringify({ error: { code: "bounded_read_failed", message: "TODO exceeds the 500-line inspection budget." } }), { status: 422, headers: { "Content-Type": "application/json" } });
      }
      const value = path === "/api/rescan" ? recovered
        : path === "/api/progress" ? { operation_id: "rescan", kind: "rescan", status: "completed", stage: "report", stage_index: 5, stage_count: 5, current_source: null, event: "inspection_completed", started_at: null, updated_at: null, completed_at: null, recent: [] }
        : path === "/api/documents" ? liveDocumentsFixture
        : path === "/api/activity" ? activityFixture
        : path === "/api/rule5-candidates" ? rule5CandidatesFixture
        : path === "/api/resume-comparison" ? emptyResumeComparisonFixture
        : path === "/api/recent-projects" ? { schema_version: 1, recent_projects: [] }
        : path.startsWith("/api/update") ? { supported: false, automatic: true, current_version: "0.0.4", state: "unsupported", available_version: null, release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: null, message: "Source mode", error: null }
        : snapshotFixture;
      return new Response(JSON.stringify(value), { headers: { "Content-Type": "application/json" } });
    }));
    const user = userEvent.setup();
    const { container } = render(<I18nProvider><App /></I18nProvider>);
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    expect(screen.getByText("0 errors")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Re-scan" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(kind === "api" ? "bounded_read_failed: TODO exceeds the 500-line inspection budget." : "Local connection interrupted");
    expect(screen.queryByText("0 errors")).not.toBeInTheDocument();
    expect(screen.getByText(/This inspection is no longer current/)).toBeVisible();
    expect(screen.getByRole("treeitem", { name: /Review Findings/ })).toHaveTextContent(/unavailable/i);
    await user.click(screen.getByRole("tab", { name: "Raw JSON" }));
    expect(JSON.parse(container.querySelector(".raw-panel pre")!.textContent!)).toEqual({ ...snapshotFixture, inspection_status: "stale" });
    expect(snapshotFixture.inspection_status).toBe("completed");

    await user.click(screen.getByRole("button", { name: "Re-scan" }));
    await waitFor(() => expect(container.querySelector(".app-shell > .sr-only[aria-live]")).toHaveTextContent("Re-scan complete"), { timeout: 3000 });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/This inspection is no longer current/)).not.toBeInTheDocument();
    expect(screen.getByText("0 errors")).toBeVisible();
    expect(JSON.parse(container.querySelector(".raw-panel pre")!.textContent!)).toEqual(recovered);
  });

  it.each(["diagnostic", "stale", "nonzero"])("does not announce a successful zero-error scan for %s", async (kind) => {
    const snapshot = structuredClone(snapshotFixture);
    snapshot.inspection_id = "rescanned";
    if (kind === "nonzero") snapshot.doctor.exit_code = 1;
    else snapshot.inspection_status = kind;
    if (kind === "diagnostic") {
      snapshot.doctor.completed = false;
      snapshot.doctor.exit_code = 2;
      snapshot.doctor.diagnostic_error = { kind: "failed", message: "Doctor unavailable" };
    }
    vi.stubGlobal("fetch", vi.fn(async (input) => {
      const path = String(input);
      const value = path === "/api/rescan" ? snapshot
        : path === "/api/progress" ? { operation_id: "rescan", kind: "rescan", status: "completed", stage: "report", stage_index: 5, stage_count: 5, current_source: null, event: "inspection_completed", started_at: null, updated_at: null, completed_at: null, recent: [] }
        : path === "/api/documents" ? liveDocumentsFixture
        : path === "/api/activity" ? activityFixture
        : path === "/api/rule5-candidates" ? rule5CandidatesFixture
        : path === "/api/resume-comparison" ? emptyResumeComparisonFixture
        : path === "/api/recent-projects" ? { schema_version: 1, recent_projects: [] }
        : path.startsWith("/api/update") ? { supported: false, automatic: true, current_version: "0.0.4", state: "unsupported", available_version: null, release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: null, message: "Source mode", error: null }
        : snapshotFixture;
      return new Response(JSON.stringify(value), { headers: { "Content-Type": "application/json" } });
    }));
    const { container } = render(<I18nProvider><App /></I18nProvider>);
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await userEvent.setup().click(screen.getByRole("button", { name: "Re-scan" }));
    const announcement = container.querySelector(".app-shell > .sr-only[aria-live]");
    await waitFor(() => expect(announcement ?? container.querySelector('.sr-only[aria-live="polite"]')).toHaveTextContent(kind === "nonzero" ? "Doctor did not pass" : "current, complete Doctor result is unavailable"), { timeout: 3000 });
    expect(screen.queryByText(/Re-scan complete. 0 errors/)).not.toBeInTheDocument();
  });
});
