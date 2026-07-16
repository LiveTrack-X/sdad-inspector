import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { I18nProvider, LOCALE_STORAGE_KEY } from "./i18n";
import { activityFixture, liveDocumentsFixture, rule5CandidatesFixture, snapshotFixture } from "./test/fixture";
import { THEME_STORAGE_KEY } from "./theme";
import type { Snapshot } from "./types";

function jsonResponse(payload: unknown = snapshotFixture, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderApp() {
  return render(<I18nProvider><App /></I18nProvider>);
}

describe("Split Inspector", () => {
  afterEach(() => { vi.useRealTimers(); });
  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(navigator, "languages", {
      configurable: true,
      value: ["en-US"],
    });
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockReturnValue({ matches: false }),
    });
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/update/check" || path === "/api/update") return jsonResponse({ supported: false, automatic: true, current_version: "0.0.3", state: "unsupported", available_version: null, release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: null, message: "Source mode", error: null });
      return jsonResponse();
    }));
  });

  it("loads a real snapshot contract into the three-pane overview", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "SI-003-browser-mvp" })).toBeVisible();
    expect(screen.getByRole("complementary", { name: "Repository controls" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Inspector details" })).toBeInTheDocument();
    expect(screen.getByText("0 errors")).toBeVisible();
    expect(screen.getByText("presented, not executed")).toBeVisible();
    expect(screen.getByRole("button", { name: "Manual" })).toHaveAttribute("aria-label", "Manual");
    expect(screen.getByRole("button", { name: "AUTO 15s" })).toHaveAttribute("aria-label", "AUTO 15s");
    expect(screen.getByRole("button", { name: "Re-scan" })).toHaveAttribute("aria-label", "Re-scan");
    expect(document.querySelector('.brand-mark img')).toHaveAttribute("src", "/sdad-inspector-logo.png");
    expect(document.querySelector(".product-banner")).not.toBeInTheDocument();
    const request = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(request[1]?.headers);
    expect(headers.get("X-SDAD-Session")).toBe("test-session-token");
  });

  it("opens the Inspector shell and in-app chooser on a true first launch", async () => {
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/snapshot") return jsonResponse({ error: { code: "project_required", message: "Choose a project." } }, 422);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/update/check") return jsonResponse({ supported: false, automatic: true, current_version: "0.0.3", state: "unsupported", available_version: null, release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: null, message: "Source mode", error: null });
      return jsonResponse();
    });

    renderApp();
    expect(await screen.findByRole("heading", { name: "Choose an SDAD project" })).toBeVisible();
    expect(screen.getByRole("dialog", { name: "Open SDAD project" })).toBeVisible();
    expect(screen.getByText("No recent projects yet.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open the SDAD Inspector repository" })).toHaveTextContent("Created by LiveTrack");
  });

  it("offers persisted whole-UI zoom controls from the action menu", async () => {
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("button", { name: "More actions" }));
    expect(screen.getByText("110%", { selector: "output" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Increase UI scale" }));
    expect(document.documentElement).toHaveAttribute("data-ui-scale", "120");
    expect(window.localStorage.getItem("sdad-inspector:ui-scale:v1")).toBe("120");
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([path]) => path === "/api/preferences")).toBe(true));
  });

  it("keeps crowded engine, tree, and owner-gate text available without collision-only labels", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "SI-003-browser-mvp" })).toBeVisible();
    expect(screen.getByTitle("Official SDAD Protocol · official-sdad-3")).toHaveTextContent("SDAD 3.2.2");

    const tree = screen.getByRole("complementary", { name: "Repository controls" });
    expect(within(tree).getByTitle("SPEC/SPEC-COMPLETE.md")).toBeVisible();
    expect(within(tree).getByTitle("SI-003-browser-mvp")).toBeVisible();

    const inspector = screen.getByRole("complementary", { name: "Inspector details" });
    expect(within(inspector).getAllByTitle("Approval unobserved")).toHaveLength(4);
  });

  it("shows a verified product update and starts the replacement handoff", async () => {
    const user = userEvent.setup();
    const ready = { supported: true, automatic: true, current_version: "0.0.2", state: "ready", available_version: "0.0.3", release_url: "https://github.com/LiveTrack-X/sdad-inspector/releases/tag/v0.0.3", downloaded_bytes: 100, total_bytes: 100, checked_at: "2026-07-16T00:00:00Z", message: "ready", error: null };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/update/check") return jsonResponse(ready);
      if (path === "/api/update/apply") return jsonResponse({ ...ready, state: "applying", message: "applying" });
      return jsonResponse();
    });
    renderApp();
    expect(await screen.findByText("SDAD Inspector 0.0.3 is verified and ready")).toBeVisible();
    expect(screen.getByText(/replace this portable executable in \d+ seconds/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Restart and update" }));
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([path]) => path === "/api/update/apply")).toBe(true));
    expect(await screen.findByText("Restarting to apply the verified update…")).toBeVisible();
  });

  it("acknowledges a successful replacement and lets the user dismiss its one-time notice", async () => {
    const user = userEvent.setup();
    const updated = { supported: true, automatic: true, current_version: "0.0.3", state: "updated", available_version: "0.0.3", release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: "2026-07-16T00:00:00Z", message: "updated", error: null };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/update/check") return jsonResponse(updated);
      if (path === "/api/update/acknowledge") return jsonResponse({ ...updated, state: "up_to_date", available_version: null, message: null });
      return jsonResponse();
    });

    renderApp();
    expect(await screen.findByText("Product update completed")).toBeVisible();
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([path]) => path === "/api/update/acknowledge")).toBe(true));
    const acknowledgement = vi.mocked(fetch).mock.calls.find(([path]) => path === "/api/update/acknowledge");
    expect(acknowledgement?.[1]?.method).toBe("POST");
    expect(new Headers(acknowledgement?.[1]?.headers).get("X-SDAD-Session")).toBe("test-session-token");

    await user.click(screen.getByRole("button", { name: "Dismiss update notification" }));
    expect(screen.queryByText("Product update completed")).not.toBeInTheDocument();
  });

  it("filters the repository tree and updates the selected field details", async () => {
    const user = userEvent.setup();
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.type(within(tree).getByPlaceholderText("Filter controls…"), "TODO");
    expect(within(tree).getByText("TODO")).toBeVisible();
    expect(within(tree).queryByText("Active SPEC")).not.toBeInTheDocument();
    await user.click(within(tree).getByText("TODO"));
    const center = screen.getByRole("main", { name: "Workspace view" });
    expect(await within(center).findByRole("heading", { name: "Open Implementation Items" })).toBeVisible();
    expect(within(center).getByText(/Build the live workspace/)).toBeVisible();
  });

  it("uses the repository tree as navigation for the center workspace", async () => {
    const user = userEvent.setup();
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    const center = screen.getByRole("main", { name: "Workspace view" });

    await user.click(within(tree).getByText("State"));
    expect(within(center).getByRole("heading", { name: "Repository state" })).toBeVisible();
    expect(within(center).getByText("packet execution")).toBeVisible();

    await user.click(within(tree).getByText("Active SPEC"));
    expect(await within(center).findByRole("heading", { name: "Active Product SPEC" })).toBeVisible();
    expect(within(center).getAllByText("SPEC/SPEC-COMPLETE.md").length).toBeGreaterThan(0);

    await user.click(within(tree).getByText("Review Findings"));
    expect(within(center).getByRole("heading", { name: "Review Findings" })).toBeVisible();

    await user.click(within(center).getByRole("tab", { name: "Overview" }));
    expect(within(center).getByRole("heading", { name: "SI-003-browser-mvp" })).toBeVisible();
  });

  it("shows service-emitted scan stage, current source, and recent work while scanning", async () => {
    const user = userEvent.setup();
    let finishRescan: ((response: Response) => void) | undefined;
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const path = String(input);
      if (path === "/api/progress") {
        return Promise.resolve(jsonResponse({
          operation_id: "scan-1",
          kind: "rescan",
          status: "running",
          stage: "controls",
          stage_index: 3,
          stage_count: 5,
          current_source: "sdad-state.yaml",
          event: "control_source_read",
          started_at: "2026-07-15T00:00:00Z",
          updated_at: "2026-07-15T00:00:01Z",
          completed_at: null,
          recent: [
            { stage: "doctor", source: "scripts/sdad.py", event: "doctor_started", at: "2026-07-15T00:00:00Z" },
            { stage: "controls", source: "sdad-state.yaml", event: "control_source_read", at: "2026-07-15T00:00:01Z" },
          ],
        }));
      }
      if (path === "/api/rescan") {
        return new Promise<Response>((resolve) => { finishRescan = resolve; });
      }
      return Promise.resolve(jsonResponse());
    });

    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("button", { name: "Re-scan" }));
    const progressHeading = await screen.findByRole("heading", { name: "Inspection in progress" });
    const progressPanel = progressHeading.closest("section");
    expect(progressPanel).not.toBeNull();
    expect(within(progressPanel!).getAllByText("Control files").length).toBeGreaterThan(0);
    expect(within(progressPanel!).getAllByText("sdad-state.yaml").length).toBeGreaterThan(0);
    expect(within(progressPanel!).getByText("scripts/sdad.py")).toBeVisible();

    finishRescan?.(jsonResponse({ ...snapshotFixture, inspection_id: "rescanned" }));
    expect(await screen.findByText(/Re-scan complete/)).toBeInTheDocument();
  });

  it("shows packet-tagged TODO, observed files, commits, and handoffs on the overview", async () => {
    renderApp();
    expect(await screen.findByRole("heading", { name: "Current packet TODO" })).toBeVisible();
    expect(await screen.findByText("Build the live workspace.")).toBeVisible();
    expect(await screen.findByText("Select the Split Inspector.")).toBeVisible();
    expect(await screen.findByText("web/src/App.tsx")).toBeVisible();
    expect(await screen.findByText("Build the browser MVP")).toBeVisible();
    expect(await screen.findByText("Progress handoff")).toBeVisible();
    expect(screen.getByText(/does not prove the packet caused/)).toBeVisible();
  });

  it("uses one packet-tagged TODO source for the tree and overview, including source sections", async () => {
    const documents = {
      ...liveDocumentsFixture,
      documents: liveDocumentsFixture.documents.map((document) => document.roles.includes("todo") ? {
        ...document,
        content: "# Open Implementation Items\n\n## Active Work\n\n- [ ] [packet:SI-003-browser-mvp] First active task.\n- [ ] [packet:SI-003-browser-mvp] Second active task.\n- [ ] [packet:SI-003-browser-mvp] Third active task.\n\n## Release / Production Readiness\n\n- [ ] [packet:SI-003-browser-mvp] Owner-gated release task.\n",
      } : document),
    };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(documents);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/snapshot") return jsonResponse({ ...snapshotFixture, state: { ...snapshotFixture.state, ledger: { ...snapshotFixture.state.ledger, todo_open: 3 } } });
      return jsonResponse();
    });

    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    const todoNode = within(tree).getByText("TODO").closest('[role="treeitem"]');
    expect(todoNode).not.toBeNull();
    expect(within(todoNode as HTMLElement).getByText("4")).toBeVisible();
    expect(screen.getByRole("heading", { name: /Remaining work 4/ })).toBeVisible();
    expect(screen.getByText("Source section: Release / Production Readiness")).toBeVisible();
  });

  it("opens routed documents in the safe Markdown reader without executing raw HTML", async () => {
    const user = userEvent.setup();
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByRole("treeitem", { name: /review-findings\.md/ }));
    const center = screen.getByRole("main", { name: "Workspace view" });
    expect(await within(center).findByRole("heading", { name: "Review Findings" })).toBeVisible();

    await user.click(within(tree).getByText("Active SPEC"));
    expect(await within(center).findByText("<script>window.BAD = true</script>")).toBeVisible();
    expect(Array.from(document.querySelectorAll("script")).some((element) => element.textContent?.includes("window.BAD"))).toBe(false);
    expect((window as unknown as { BAD?: boolean }).BAD).toBeUndefined();
    expect(within(center).getByRole("group", { name: "Build badge" })).toBeVisible();
    expect(within(center).getByRole("link", { name: "Open image" })).toHaveAttribute("href", "https://img.shields.io/badge/build-pass-green");
    expect(within(center).getByRole("group", { name: "Local diagram" })).toHaveTextContent("Image not displayed in the read-only viewer");
    expect(within(center).queryByText(/!\[Build badge\]/)).not.toBeInTheDocument();
  });

  it("navigates live Markdown headings and keeps routed documents in a responsive disclosure", async () => {
    const user = userEvent.setup();
    const documents = {
      ...liveDocumentsFixture,
      documents: liveDocumentsFixture.documents.map((item) => item.roles.includes("active_spec") ? {
        ...item,
        content: "# Active Product SPEC\n\nThe current contract is readable.\n\n## Acceptance boundary\n\nEvidence stays read-only.\n",
      } : item),
    };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(documents);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      return jsonResponse();
    });

    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("Active SPEC"));
    const center = screen.getByRole("main", { name: "Workspace view" });
    const routeToggle = within(center).getByRole("button", { name: "Show 2 routed documents" });
    expect(routeToggle).toHaveAttribute("aria-expanded", "false");
    expect(within(center).queryByRole("button", { name: "review-findings.md" })).not.toBeInTheDocument();
    await user.click(routeToggle);
    expect(within(center).getByRole("button", { name: "Hide 2 routed documents" })).toHaveAttribute("aria-expanded", "true");
    expect(within(center).getByRole("button", { name: "review-findings.md" })).toBeVisible();

    const outline = within(center).getByRole("combobox", { name: "Document outline" });
    const option = within(outline).getByRole("option", { name: "— Acceptance boundary" }) as HTMLOptionElement;
    fireEvent.change(outline, { target: { value: option.value } });
    expect(within(center).getByRole("heading", { name: "Acceptance boundary" })).toHaveFocus();
    expect(within(center).getByText("2 headings")).toBeVisible();
  });

  it("opens the active SPEC relationship in the same central Markdown reader", async () => {
    const user = userEvent.setup();
    renderApp();
    const center = await screen.findByRole("main", { name: "Workspace view" });
    const relationships = within(center).getByRole("heading", { name: "Relationships" }).closest("section");
    expect(relationships).not.toBeNull();
    await user.click(within(relationships!).getByRole("button", { name: "SPEC/SPEC-COMPLETE.md" }));
    expect(await within(center).findByRole("heading", { name: "Active Product SPEC" })).toBeVisible();
    expect(within(center).getByRole("heading", { name: "Active Product SPEC" }).parentElement).toHaveTextContent("The current contract is readable.");
  });

  it("exposes an overview tree entry and keyboard-resizable pane separators", async () => {
    const user = userEvent.setup();
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("State"));
    await user.click(within(tree).getByRole("treeitem", { name: "Overview" }));
    expect(screen.getByRole("heading", { name: "SI-003-browser-mvp" })).toBeVisible();
    const separator = screen.getByRole("separator", { name: "Resize repository pane" });
    expect(separator).toHaveAttribute("aria-valuenow", "280");
    separator.focus();
    await user.keyboard("{ArrowRight}");
    expect(separator).toHaveAttribute("aria-valuenow", "296");
    expect(localStorage.getItem("sdad-inspector:pane-widths:v1")).toContain("296");
  });

  it("pastes a project path only after the explicit dialog action", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/clipboard/project-path") return jsonResponse({ project_root: "C:\\work\\pasted-project" });
      return jsonResponse();
    });
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("button", { name: /C:\\work\\sdad-project/ }));
    const input = screen.getByRole("textbox", { name: "Project root" });
    expect(input).toHaveValue("C:\\work\\sdad-project");
    await user.click(screen.getByRole("button", { name: "Paste" }));
    expect(input).toHaveValue("C:\\work\\pasted-project");
    const pasteCall = vi.mocked(fetch).mock.calls.find(([path]) => path === "/api/clipboard/project-path");
    expect(pasteCall?.[1]?.method).toBe("POST");
  });

  it("keeps picker cancellation inert and opens an explicitly selected folder", async () => {
    const user = userEvent.setup();
    let pickerCalls = 0;
    const pickedRoot = "C:\\work\\picked-project";
    const pickedSnapshot = { ...snapshotFixture, project: { ...snapshotFixture.project, root: pickedRoot, name: "picked-project" } };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/project-picker") {
        pickerCalls += 1;
        return jsonResponse(pickerCalls === 1
          ? { selected: false, project_root: null }
          : { selected: true, project_root: pickedRoot });
      }
      if (path === "/api/project") return jsonResponse(pickedSnapshot);
      if (path === "/api/progress") return jsonResponse({ operation_id: "open", kind: "project_open", status: "completed", stage: "report", stage_index: 5, stage_count: 5, current_source: null, event: "inspection_completed", started_at: null, updated_at: null, completed_at: null, recent: [] });
      return jsonResponse();
    });
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("button", { name: /C:\\work\\sdad-project/ }));
    const input = screen.getByRole("textbox", { name: "Project root" });
    await user.click(screen.getByRole("button", { name: "Browse" }));
    await waitFor(() => expect(pickerCalls).toBe(1));
    expect(input).toHaveValue("C:\\work\\sdad-project");
    expect(vi.mocked(fetch).mock.calls.filter(([path]) => path === "/api/project")).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "Browse" }));
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.filter(([path]) => path === "/api/project")).toHaveLength(1));
    expect(await screen.findByRole("button", { name: pickedRoot })).toBeVisible();
  });

  it("shows an inline failure when explicit clipboard paste is unavailable", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/clipboard/project-path") return jsonResponse({ error: { code: "clipboard_unavailable", message: "Clipboard is unavailable." } }, 422);
      return jsonResponse();
    });
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("button", { name: /C:\\work\\sdad-project/ }));
    const input = screen.getByRole("textbox", { name: "Project root" });
    await user.click(screen.getByRole("button", { name: "Paste" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Clipboard is unavailable.");
    expect(input).toHaveValue("C:\\work\\sdad-project");
  });

  it("does not run hidden workspace refresh loops in manual mode", async () => {
    vi.useFakeTimers();
    const rendered = renderApp();
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    const count = (path: string) => vi.mocked(fetch).mock.calls.filter(([value]) => value === path).length;
    expect(count("/api/documents")).toBe(1);
    expect(count("/api/activity")).toBe(1);
    expect(count("/api/rule5-candidates")).toBe(1);
    await act(async () => { vi.advanceTimersByTime(60_000); await Promise.resolve(); await Promise.resolve(); });
    expect(count("/api/documents")).toBe(1);
    expect(count("/api/activity")).toBe(1);
    expect(count("/api/rule5-candidates")).toBe(1);
    rendered.unmount();
    vi.useRealTimers();
  });

  it("runs explicit AUTO mode once per 15 seconds and does not overlap a pending scan", async () => {
    vi.useFakeTimers();
    let finishRescan: ((response: Response) => void) | undefined;
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const path = String(input);
      if (path === "/api/documents") return Promise.resolve(jsonResponse(liveDocumentsFixture));
      if (path === "/api/activity") return Promise.resolve(jsonResponse(activityFixture));
      if (path === "/api/rule5-candidates") return Promise.resolve(jsonResponse(rule5CandidatesFixture));
      if (path === "/api/recent-projects") return Promise.resolve(jsonResponse({ schema_version: 1, recent_projects: [] }));
      if (path === "/api/progress") return Promise.resolve(jsonResponse({ operation_id: "auto", kind: "rescan", status: "completed", stage: "report", stage_index: 5, stage_count: 5, current_source: null, event: "inspection_completed", started_at: null, updated_at: null, completed_at: null, recent: [] }));
      if (path === "/api/rescan") return new Promise<Response>((resolve) => { finishRescan = resolve; });
      return Promise.resolve(jsonResponse());
    });
    const rendered = renderApp();
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    const auto = screen.getByRole("button", { name: "AUTO 15s" });
    await act(async () => { auto.click(); await Promise.resolve(); });
    const count = (path: string) => fetchMock.mock.calls.filter(([value]) => value === path).length;
    expect(count("/api/documents")).toBe(1);
    expect(count("/api/activity")).toBe(1);
    expect(count("/api/rule5-candidates")).toBe(1);
    await act(async () => { vi.advanceTimersByTime(15_100); await Promise.resolve(); });
    expect(fetchMock.mock.calls.filter(([path]) => path === "/api/rescan")).toHaveLength(1);
    await act(async () => { vi.advanceTimersByTime(30_000); await Promise.resolve(); });
    expect(fetchMock.mock.calls.filter(([path]) => path === "/api/rescan")).toHaveLength(1);
    expect(count("/api/documents")).toBe(1);
    expect(count("/api/activity")).toBe(1);
    expect(count("/api/rule5-candidates")).toBe(1);
    finishRescan?.(jsonResponse({ ...snapshotFixture, inspection_id: "auto-rescanned" }));
    await act(async () => { await Promise.resolve(); vi.advanceTimersByTime(1_000); await Promise.resolve(); });
    expect(count("/api/documents")).toBe(2);
    expect(count("/api/activity")).toBe(2);
    expect(count("/api/rule5-candidates")).toBe(2);
    expect(localStorage.getItem("sdad-inspector:rescan-mode:v1")).toBe("auto");
    rendered.unmount();
    vi.useRealTimers();
  });

  it("shows the official control loop without inferring a current stage", async () => {
    const user = userEvent.setup();
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("Development Flow"));
    const center = screen.getByRole("main", { name: "Workspace view" });
    const officialFlow = within(center).getByRole("region", { name: "Official SDAD control loop" });
    expect(within(officialFlow).getByText("Plan")).toBeVisible();
    expect(within(officialFlow).getByText("Route")).toBeVisible();
    expect(within(officialFlow).getByText("Implement")).toBeVisible();
    expect(within(officialFlow).getByText("Verify")).toBeVisible();
    expect(within(officialFlow).getByText("Report")).toBeVisible();
    expect(within(officialFlow).getByText("Doctor structural check")).toBeVisible();
    expect(within(officialFlow).getByText("Execution evidence")).toBeVisible();
    expect(within(officialFlow).getByText("Owner-accepted")).toBeVisible();
    expect(within(center).getByText("New file")).toHaveAttribute("title", "Raw Git status: ??");
    expect(center.querySelector('[aria-current="step"]')).toBeNull();
    expect(within(center).getByText("Gate declared · approval evidence unobserved")).toBeVisible();
    expect(within(center).getByText("Inspector cannot perform protected actions (read-only).")).toBeVisible();
    expect(within(center).getByText("No current handoff is declared.")).toBeVisible();
  });

  it("shows an explicit current packet TODO, highlights its official phase, and opens evidence documents", async () => {
    const user = userEvent.setup();
    const documents = {
      ...liveDocumentsFixture,
      documents: liveDocumentsFixture.documents.map((document) => document.roles.includes("todo")
        ? {
            ...document,
            content: "# Open Implementation Items\n\n## Active Work\n\n- [ ] [packet:SI-003-browser-mvp] [phase:Implement] [current] Build the exact declared-work view.\n- [ ] [packet:SI-003-browser-mvp] Keep the remaining work visible.\n",
          }
        : document),
    };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(documents);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/update/check" || path === "/api/update") return jsonResponse({ supported: false, automatic: true, current_version: "0.0.3", state: "unsupported", available_version: null, release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: null, message: "Source mode", error: null });
      return jsonResponse();
    });

    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("Development Flow"));
    const center = screen.getByRole("main", { name: "Workspace view" });
    expect(within(center).getByRole("heading", { name: "Current declared work" })).toBeVisible();
    expect(within(center).getByText("Build the exact declared-work view.")).toBeVisible();
    expect(within(center).getByText("Keep the remaining work visible.")).toBeVisible();
    const currentStage = center.querySelector('[aria-current="step"]');
    expect(currentStage).not.toBeNull();
    expect(currentStage).toHaveTextContent("Implement");
    expect(currentStage).toHaveTextContent("Current");

    await user.click(within(center).getByRole("button", { name: "Open evidence document review-findings.md" }));
    expect(await within(center).findByRole("heading", { name: "Review Findings" })).toBeVisible();
    expect(within(center).getByText("No active finding.")).toBeVisible();
  });

  it("uses the secondary worktree lens to drill into changed files and restore the full list", async () => {
    const user = userEvent.setup();
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("Development Flow"));
    const center = screen.getByRole("main", { name: "Workspace view" });
    const changedSection = within(center).getByRole("heading", { name: "Observed changed files" }).closest("section");
    expect(changedSection).not.toBeNull();
    expect(within(changedSection!).getByText("web/src/App.tsx")).toBeVisible();
    expect(within(changedSection!).getByText("docs/handoff.md")).toBeVisible();

    const buildFilter = within(center).getByRole("button", { name: "Filter changed files to the Implementation lens (1 paths)" });
    await user.click(buildFilter);
    expect(buildFilter).toHaveAttribute("aria-pressed", "true");
    expect(within(changedSection!).getByText("web/src/App.tsx")).toBeVisible();
    expect(within(changedSection!).queryByText("docs/handoff.md")).not.toBeInTheDocument();
    expect(within(changedSection!).getByLabelText("1 of 2 changed files")).toBeVisible();

    await user.click(within(changedSection!).getByRole("button", { name: "Clear the worktree evidence lens" }));
    expect(within(changedSection!).getByText("docs/handoff.md")).toBeVisible();
    expect(buildFilter).toHaveAttribute("aria-pressed", "false");
  });

  it("loads recent projects from stable app preferences and keeps clear history visible", async () => {
    const user = userEvent.setup();
    let cleared = false;
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects/clear") { cleared = true; return jsonResponse({ schema_version: 1, recent_projects: [] }); }
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: cleared ? [] : [
        { path: snapshotFixture.project.root, name: snapshotFixture.project.name, opened_at: "2026-07-15T06:00:00Z" },
        { path: "C:\\work\\legacy-project", name: "legacy-project", opened_at: "2026-07-14T06:00:00Z" },
      ] });
      if (path === "/api/snapshot") return jsonResponse(snapshotFixture);
      expect(init?.method).not.toBe("POST");
      return jsonResponse();
    });
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("button", { name: /C:\\work\\sdad-project/ }));
    expect(screen.getByRole("button", { name: /legacy-project/ })).toBeVisible();
    const clear = screen.getByRole("button", { name: "Clear history" });
    expect(clear).toBeEnabled();
    await user.click(clear);
    expect(await screen.findByText("No recent projects yet.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Clear history" })).toBeDisabled();
    expect(vi.mocked(fetch).mock.calls.some(([path, init]) => path === "/api/recent-projects/clear" && init?.method === "POST")).toBe(true);
  });

  it("previews a Rule 5 proposal as Markdown before an explicit local Save As export", async () => {
    const user = userEvent.setup();
    const preview = {
      markdown: "# Rule 5 Proposal: R5-FIND-SI-010-001\n\nStatus: Candidate - not an active rule or owner acceptance\n\n## Operational Rule\n\nUse one inspection cycle.\n",
      sha256: "b".repeat(64),
      suggested_filename: "R5-FIND-SI-010-001.md",
    };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/rule5/preview") return jsonResponse(preview);
      if (path === "/api/rule5/export") return jsonResponse({ ...preview, saved: true, cancelled: false, path: "C:\\exports\\R5-FIND-SI-010-001.md" });
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      return jsonResponse();
    });
    renderApp();
    const tree = await screen.findByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("Rule 5 proposals"));
    await user.click(screen.getByRole("button", { name: "Extract rule" }));
    expect(await screen.findByRole("heading", { name: "Rule 5 Proposal: R5-FIND-SI-010-001" })).toBeVisible();
    const save = screen.getByRole("button", { name: "Save local .md" });
    expect(save).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /reviewed this exact preview/ }));
    expect(save).toBeEnabled();
    await user.click(save);
    expect(await screen.findByRole("status")).toHaveTextContent("Rule 5 proposal saved to C:\\exports\\R5-FIND-SI-010-001.md. It is not active.");
    const exportCall = vi.mocked(fetch).mock.calls.find(([path]) => path === "/api/rule5/export");
    expect(exportCall?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(exportCall?.[1]?.body))).toMatchObject({ confirmed: true, preview_sha256: preview.sha256 });
  });

  it("switches and restores a locally persisted dark theme", async () => {
    const user = userEvent.setup();
    const first = renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    expect(document.documentElement).toHaveAttribute("data-theme", "light");

    await user.click(screen.getByRole("button", { name: "Use dark theme" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");

    first.unmount();
    renderApp();
    expect(await screen.findByRole("button", { name: "Use light theme" })).toBeVisible();
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });

  it("shows preserved snapshot evidence in the Raw JSON tab", async () => {
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    await user.click(screen.getByRole("tab", { name: "Raw JSON" }));
    expect(screen.getByText(/"snapshot_schema_version": 2/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Copy JSON" })).toBeEnabled();
  });

  it("shows evidence bodies below metadata for JSON, YAML, and Markdown", async () => {
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    const tree = screen.getByRole("complementary", { name: "Repository controls" });

    await user.click(within(tree).getByText("Doctor Report (JSON)"));
    expect(screen.getByRole("heading", { name: "Evidence metadata" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Evidence body" })).toBeVisible();
    expect(screen.getByLabelText("Evidence body: Doctor Report")).toHaveTextContent('"schema_version": 2');

    await user.click(within(tree).getByText("State (YAML)"));
    expect(screen.getByLabelText("Evidence body: State Evidence")).toHaveTextContent("version: 2");

    await user.click(within(tree).getByText("Active SPEC (Markdown)"));
    const markdown = screen.getByLabelText("Evidence body: Active SPEC");
    expect(within(markdown).getByRole("heading", { name: "Active Product SPEC" })).toBeVisible();
    expect(markdown).toHaveTextContent("The current contract is readable.");
  });

  it("re-scans through the fixed POST route and announces the result", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input) => {
      if (String(input) === "/api/documents") return jsonResponse(liveDocumentsFixture);
      if (String(input) === "/api/activity") return jsonResponse(activityFixture);
      if (String(input) === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (String(input) === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (String(input) === "/api/progress") return jsonResponse({
        operation_id: "rescan",
        kind: "rescan",
        status: "completed",
        stage: "report",
        stage_index: 5,
        stage_count: 5,
        current_source: "Inspector snapshot (memory)",
        event: "inspection_completed",
        started_at: "2026-07-15T00:00:00Z",
        updated_at: "2026-07-15T00:00:01Z",
        completed_at: "2026-07-15T00:00:01Z",
        recent: [],
      });
      if (String(input) === "/api/rescan") {
        return jsonResponse({ ...snapshotFixture, inspection_id: "rescanned" });
      }
      return jsonResponse();
    });
    renderApp();
    await screen.findByRole("heading", { name: "SI-003-browser-mvp" });
    const tree = screen.getByRole("complementary", { name: "Repository controls" });
    await user.click(within(tree).getByText("Active SPEC"));
    expect(await screen.findByRole("heading", { name: "Active Product SPEC" })).toBeVisible();
    const center = screen.getByRole("main", { name: "Workspace view" });
    const workspaceScroller = center.querySelector<HTMLDivElement>(".overview-scroll");
    expect(workspaceScroller).not.toBeNull();
    workspaceScroller!.scrollTop = 220;
    fireEvent.scroll(workspaceScroller!);
    await user.click(screen.getByRole("button", { name: "Re-scan" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path === "/api/rescan")).toBe(true));
    const rescanCall = fetchMock.mock.calls.find(([path]) => path === "/api/rescan");
    expect(rescanCall?.[1]?.method).toBe("POST");
    expect(await screen.findByText(/Re-scan complete/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Active Product SPEC" })).toBeVisible();
    expect(workspaceScroller).toHaveProperty("scrollTop", 220);
  });

  it("renders a recoverable error state without implying a project write", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch).mockRejectedValueOnce(new Error("offline local service"));
    renderApp();
    expect(await screen.findByRole("heading", { name: /could not load this project/i })).toBeVisible();
    expect(screen.getByText(/No project command or write was attempted/)).toBeVisible();
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse());
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "SI-003-browser-mvp" })).toBeVisible();
  });

  it("renders and navigates a missing-state diagnostic snapshot", async () => {
    const user = userEvent.setup();
    const missingStateSnapshot = {
      ...snapshotFixture,
      contracts: { ...snapshotFixture.contracts, state_schema_version: null },
      doctor: {
        ...snapshotFixture.doctor,
        state_schema_version: null,
        summary: { errors: 1, warnings: 0 },
        findings: [{
          id: "state.missing",
          severity: "error",
          path: "sdad-state.yaml",
          line: null,
          message: "The project does not have a readable regular sdad-state.yaml file.",
          evidence: "required state status: missing",
          remediation: "Create the root-level sdad-state.yaml for this stateful workflow.",
        }],
        exit_code: 1,
      },
      state: {
        ...snapshotFixture.state,
        available: false,
        schema_version: null,
        active_spec: null,
        active_packet: null,
        validation_for: null,
        validation: [],
        owner_gates: [],
        routed_docs: [],
        current_handoff: null,
      },
    } as unknown as Snapshot;
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(missingStateSnapshot));

    renderApp();
    expect(await screen.findByRole("heading", { name: "Doctor Summary" })).toBeVisible();
    expect(screen.getByText("The project does not have a readable regular sdad-state.yaml file.")).toBeVisible();
    await user.click(screen.getByRole("treeitem", { name: /Current Handoff/ }));
    const inspector = screen.getByRole("complementary", { name: "Inspector details" });
    expect(within(inspector).getByText("Not declared")).toBeVisible();
    await user.click(screen.getByText("Development Flow"));
    const flow = screen.getByRole("region", { name: "Official SDAD control loop" });
    expect(within(flow).getByText("Plan")).toBeVisible();
    expect(within(flow).getAllByText("Failed").length).toBe(2);
    expect(within(flow).getAllByText("Unobserved").length).toBeGreaterThan(0);
  });

  it("selects Korean for a Korean browser while preserving repository evidence", async () => {
    Object.defineProperty(navigator, "languages", {
      configurable: true,
      value: ["ko-KR", "en-US"],
    });
    const documents = {
      ...liveDocumentsFixture,
      documents: liveDocumentsFixture.documents.map((document) => document.roles.includes("todo")
        ? { ...document, content: "# TODO\n\n## Active Work\n\n- [ ] [packet:SI-003-browser-mvp] [current] [phase:Implement] 현재 작업을 정확히 표시한다.\n" }
        : document),
    };
    vi.mocked(fetch).mockImplementation(async (input) => {
      const path = String(input);
      if (path === "/api/documents") return jsonResponse(documents);
      if (path === "/api/activity") return jsonResponse(activityFixture);
      if (path === "/api/rule5-candidates") return jsonResponse(rule5CandidatesFixture);
      if (path === "/api/recent-projects") return jsonResponse({ schema_version: 1, recent_projects: [] });
      if (path === "/api/update/check" || path === "/api/update") return jsonResponse({ supported: false, automatic: true, current_version: "0.0.3", state: "unsupported", available_version: null, release_url: null, downloaded_bytes: 0, total_bytes: 0, checked_at: null, message: "Source mode", error: null });
      return jsonResponse();
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "SI-003-browser-mvp" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Doctor 요약" })).toBeVisible();
    expect(screen.getByText("오류 0개")).toBeVisible();
    expect(screen.getByRole("combobox", { name: "언어" })).toHaveValue("ko");
    expect(document.documentElement).toHaveAttribute("lang", "ko");
    expect(screen.getByText("Build the selected Split Inspector browser UI.")).toBeVisible();
    expect(screen.getByText("npm run build")).toBeVisible();
    const user = userEvent.setup();
    await user.click(screen.getByText("개발 흐름"));
    const flow = screen.getByRole("region", { name: "공식 SDAD 제어 루프" });
    for (const stage of ["Plan", "Route", "Implement", "Verify", "Report"]) {
      expect(within(flow).getByText(stage)).toBeVisible();
    }
    expect(screen.getByRole("heading", { name: "현재 선언된 작업" })).toBeVisible();
    expect(screen.getByText("현재 작업을 정확히 표시한다.")).toBeVisible();
    expect(screen.getByText("근거 문서")).toBeVisible();
    expect(screen.getByRole("main", { name: "작업공간 보기" }).querySelector('[aria-current="step"]')).toHaveTextContent("Implement");
  });

  it("switches languages explicitly and restores the versioned preference", async () => {
    Object.defineProperty(navigator, "languages", {
      configurable: true,
      value: ["ko-KR"],
    });
    const user = userEvent.setup();
    const first = renderApp();
    const language = await screen.findByRole("combobox", { name: "언어" });
    await user.selectOptions(language, "en");
    expect(screen.getByRole("heading", { name: "Doctor Summary" })).toBeVisible();
    expect(document.documentElement).toHaveAttribute("lang", "en");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("en");

    first.unmount();
    renderApp();
    expect(await screen.findByRole("combobox", { name: "Language" })).toHaveValue("en");
  });
});
