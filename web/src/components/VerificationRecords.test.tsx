import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getVerificationReceiptList, inspectVerificationReceipt, revealPath } from "../api";
import { I18nProvider, LOCALE_STORAGE_KEY } from "../i18n";
import { snapshotFixture } from "../test/fixture";
import type { VerificationReceiptInspection, VerificationReceiptList } from "../verificationReceipts";
import { verificationCopy } from "../verificationCopy";
import { VerificationRecords } from "./VerificationRecords";

vi.mock("../api", () => ({ getVerificationReceiptList: vi.fn(), inspectVerificationReceipt: vi.fn(), revealPath: vi.fn().mockResolvedValue({ revealed: true }) }));
const envelope = { version: 1 as const, project_root: snapshotFixture.project.root, packet: snapshotFixture.state.active_packet!.id, read_at: "2026-09-20T06:00:00Z", revision: "a".repeat(64) };
const list = (paths = ["evidence/run.json"]): VerificationReceiptList => ({ ...envelope, offset: 0, total: paths.length, next_offset: null, paths });
const fixture = (path = "evidence/run.json"): VerificationReceiptInspection => ({
  ...envelope,
  observation: { path, error: null, source_match: "changed", log_match: "matched",
    sources: [{ path: "src/main.py", match: "changed", reason: "Source digest differs" }],
    receipt: {
      schema: "sdad.verification-receipt", version: 1, id: "run-1", packet: snapshotFixture.state.active_packet!.id,
      requirement: "R-1: parser boundary", scope: "parser regression", cwd: ".",
      command: { argv: ["python", "-m", "unittest"], python_version: "3.12", platform: "test" },
      started_at: "2026-09-19T06:00:00Z", ended_at: "2026-09-19T06:00:01Z", outcome: "passed", exit_code: 0,
      source_stability: "stable", sources: [], log: { path: "evidence/run.log", sha256: "a".repeat(64), bytes: 0, total_bytes: 100, truncated: true, complete: true }, limits: [],
    },
  },
});
function show(snapshot = snapshotFixture) { return render(<I18nProvider><VerificationRecords snapshot={snapshot} /></I18nProvider>); }
async function read() {
  fireEvent.click(screen.getByRole("button", { name: "Read verification records" }));
  await screen.findByRole("button", { name: "Read records again" });
}
async function select(path = "evidence/run.json") {
  fireEvent.click(await screen.findByRole("button", { name: `Inspect record: ${path}` }));
  await screen.findByRole("article", { name: "Selected record" });
}

describe("verification receipt navigation", () => {
  beforeEach(() => {
    vi.mocked(getVerificationReceiptList).mockReset();
    vi.mocked(inspectVerificationReceipt).mockReset();
    vi.mocked(revealPath).mockClear();
  });
  it("lists only on demand, then compares only the selected record without inferring current success", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(fixture());
    show(); expect(getVerificationReceiptList).not.toHaveBeenCalled();
    await read();
    expect(inspectVerificationReceipt).not.toHaveBeenCalled();
    expect(screen.queryByText("Command succeeded")).not.toBeInTheDocument();
    await select();
    expect(inspectVerificationReceipt).toHaveBeenCalledWith(envelope.project_root, "evidence/run.json", envelope.revision);
    expect(screen.getByText("Command succeeded")).toBeInTheDocument();
    expect(screen.getByText("Source identity: Changed")).toBeInTheDocument();
    expect(screen.getByText(/do not establish coverage/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Recorded command and sources"));
    expect(screen.getByText(/Only a bounded portion/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show retained log" }));
    expect(revealPath).toHaveBeenCalledWith("evidence/run.log");
  });
  it("reaches the eleventh record without inspecting the first page and retains route revision", async () => {
    const paths = Array.from({ length: 11 }, (_, i) => `evidence/${i + 1}.json`);
    vi.mocked(getVerificationReceiptList)
      .mockResolvedValueOnce({ ...list(paths.slice(0, 10)), total: 11, next_offset: 10 })
      .mockResolvedValueOnce({ ...list(paths.slice(10)), total: 11, offset: 10 })
      .mockResolvedValueOnce({ ...list(paths.slice(0, 10)), total: 11, next_offset: 10 });
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(fixture(paths[10]));
    show(); await read();
    expect(screen.getByText("1–10 / 11")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous records" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next records" }));
    await screen.findByText("11–11 / 11");
    expect(getVerificationReceiptList).toHaveBeenLastCalledWith(envelope.project_root, 10, envelope.revision);
    expect(inspectVerificationReceipt).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Next records" })).toBeDisabled();
    await select(paths[10]);
    fireEvent.click(screen.getByRole("button", { name: "Previous records" }));
    await screen.findByText("1–10 / 11");
    expect(screen.queryByText("Command succeeded")).not.toBeInTheDocument();
  });
  it("shows an invalid selected record without blocking another selection", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["bad.json", "evidence/run.json"]));
    vi.mocked(inspectVerificationReceipt)
      .mockResolvedValueOnce({ ...envelope, observation: { path: "bad.json", receipt: null, source_match: "unknown", log_match: "unknown", sources: [], error: "Unsupported receipt version" } })
      .mockResolvedValueOnce(fixture());
    show(); await read(); await select("bad.json");
    expect(screen.getByRole("alert")).toHaveTextContent("Unsupported receipt version");
    expect(screen.queryByText(/No verification receipts/)).not.toBeInTheDocument();
    await select();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Selected record" })).getByText("Command succeeded")).toBeInTheDocument();
  });
  it("clears a previous comparison when comparison fails and requires a fresh list", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    vi.mocked(inspectVerificationReceipt).mockResolvedValueOnce(fixture()).mockRejectedValueOnce(new Error("Routes changed; read again"));
    show(); await read(); await select();
    fireEvent.click(screen.getByRole("button", { name: "Compare record again" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Routes changed");
    expect(screen.queryByText("Command succeeded")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Read verification records" })).toBeEnabled();
  });
  it("does not keep a previous successful comparison after a failed list refresh", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValueOnce(list()).mockRejectedValueOnce(new Error("Read failed"));
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(fixture());
    show(); await read(); await select();
    fireEvent.click(screen.getByRole("button", { name: "Read records again" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Read failed");
    expect(screen.queryByText("Command succeeded")).not.toBeInTheDocument();
  });
  it.each(["project", "packet", "revision", "path"])("rejects a comparison with wrong %s binding", async kind => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    const result = fixture();
    if (kind === "project") result.project_root = "/other";
    if (kind === "packet") result.packet = "another-packet";
    if (kind === "revision") result.revision = "b".repeat(64);
    if (kind === "path") result.observation.path = "other.json";
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(result);
    show(); await read(); fireEvent.click(screen.getByRole("button", { name: "Inspect record: evidence/run.json" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("project or packet changed");
    expect(screen.queryByText("Command succeeded")).not.toBeInTheDocument();
  });
  it("rejects wrong-project lists and late comparisons after project switch", async () => {
    let resolve!: (value: VerificationReceiptInspection) => void;
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    vi.mocked(inspectVerificationReceipt).mockReturnValueOnce(new Promise(done => { resolve = done; }));
    const view = show(); await read(); fireEvent.click(screen.getByRole("button", { name: "Inspect record: evidence/run.json" }));
    const other = { ...snapshotFixture, project: { ...snapshotFixture.project, identity: "other", root: "/other-project" } };
    view.rerender(<I18nProvider><VerificationRecords snapshot={other} /></I18nProvider>);
    await act(async () => resolve(fixture()));
    expect(screen.queryByText("Command succeeded")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Read verification records" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("project or packet changed");
  });
  it("takes the packet label from the selected receipt and offers read-only connection help", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    const result = fixture(); result.observation.receipt!.packet = "old-packet";
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(result);
    show(); await read();
    expect(screen.queryByText(/Current packet:/)).not.toBeInTheDocument();
    await select(); expect(screen.getByText("Another packet: old-packet")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Connect a collected record"));
    expect(screen.getByText(/preview changes no project files/)).toBeInTheDocument();
    expect(screen.getByText(/--preview-connection/)).toBeInTheDocument();
  });
  it("keeps empty registration distinct from successful verification", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list([]));
    show(); await read();
    expect(screen.getByText(/No verification receipts are linked/)).toBeInTheDocument();
    expect(inspectVerificationReceipt).not.toHaveBeenCalled();
  });
  it("discloses incomplete output capture even when its retained bytes match and are not truncated", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    const result = fixture();
    result.observation.receipt!.log = { ...result.observation.receipt!.log, bytes: 0, total_bytes: 0, truncated: false, complete: false };
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(result);
    show(); await read(); await select();
    fireEvent.click(screen.getByText("Recorded command and sources"));
    expect(screen.getByText("Retained log identity: Matches")).toBeInTheDocument();
    expect(screen.getByText(/Output capture did not finish/)).toBeInTheDocument();
    expect(screen.queryByText(/Only a bounded portion/)).not.toBeInTheDocument();
  });
  it("disables receipt reads for stale inspections", () => {
    show({ ...snapshotFixture, inspection_status: "stale" });
    expect(screen.getByRole("button", { name: "Read verification records" })).toBeDisabled();
  });
  it("compares two explicitly inspected observations without reopening details or reading other records", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["first.json", "second.json", "unread.json"]));
    const first = fixture("first.json");
    first.observation.receipt = { ...first.observation.receipt!, packet: "OLD", scope: "owner first scope", outcome: "failed", exit_code: 7 };
    const second = fixture("second.json");
    second.read_at = "2026-09-20T07:00:00Z";
    second.observation.source_match = "matched";
    second.observation.receipt = { ...second.observation.receipt!, scope: "owner second scope" };
    vi.mocked(inspectVerificationReceipt).mockResolvedValueOnce(first).mockResolvedValueOnce(second);
    show(); await read(); await select("first.json");
    expect(screen.getByText(/Inspect another record/)).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await select("second.json");
    const table = screen.getByRole("table", { name: "Compare inspected records" });
    const comparison = within(table);
    expect(comparison.getByText("owner first scope")).toBeVisible();
    expect(comparison.getByText("owner second scope")).toBeVisible();
    expect(comparison.getByText("Command failed")).toBeVisible();
    expect(comparison.getByText("Command succeeded")).toBeVisible();
    expect(comparison.getByText("Changed")).toBeVisible();
    expect(comparison.getAllByText("Matches")).toHaveLength(3);
    expect(comparison.getByText("Another packet")).toBeVisible();
    expect(comparison.getByText("Exit code: 7")).toBeVisible();
    expect(table.querySelector('time[datetime="2026-09-20T06:00:00Z"]')).toBeVisible();
    expect(table.querySelector('time[datetime="2026-09-20T07:00:00Z"]')).toBeVisible();
    expect(screen.getByText(/not a simultaneous check or a combined completion result/)).toBeVisible();
    expect(table.parentElement).toHaveFocus();
    expect(inspectVerificationReceipt).toHaveBeenCalledTimes(2);
    expect(getVerificationReceiptList).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Recorded command and sources").closest("details")).not.toHaveAttribute("open");
  });
  it("keeps only two distinct latest observations and lets users remove or clear without new reads", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["a.json", "b.json", "c.json"]));
    vi.mocked(inspectVerificationReceipt).mockImplementation(async (_root, path) => fixture(path));
    show(); await read(); await select("a.json"); await select("b.json"); await select("c.json");
    let table = screen.getByRole("table");
    expect(within(table).queryByText("a.json")).not.toBeInTheDocument();
    expect(within(table).getByText("b.json")).toBeVisible();
    expect(within(table).getByText("c.json")).toBeVisible();
    await select("b.json");
    table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(3);
    expect(within(table).getAllByText("b.json")).toHaveLength(1);
    fireEvent.click(within(table).getByRole("button", { name: "Remove from comparison: c.json" }));
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByText(/Inspect another record/)).toHaveTextContent("b.json");
    fireEvent.click(screen.getByRole("button", { name: "Clear comparison" }));
    expect(screen.queryByText(/Inspect another record/)).not.toBeInTheDocument();
    expect(inspectVerificationReceipt).toHaveBeenCalledTimes(4);
    expect(getVerificationReceiptList).toHaveBeenCalledTimes(1);
  });
  it("retains the first observation across pinned list pages and clears both on a fresh read", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValueOnce({ ...list(["a.json"]), total: 11, next_offset: 10 })
      .mockResolvedValueOnce({ ...list(["b.json"]), offset: 10, total: 11 })
      .mockResolvedValueOnce(list(["a.json"]));
    vi.mocked(inspectVerificationReceipt).mockImplementation(async (_root, path) => fixture(path));
    show(); await read(); await select("a.json");
    fireEvent.click(screen.getByRole("button", { name: "Next records" }));
    await screen.findByText("11–11 / 11"); await select("b.json");
    expect(within(screen.getByRole("table")).getByText("a.json")).toBeVisible();
    expect(inspectVerificationReceipt).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole("button", { name: "Read records again" }));
    await screen.findByRole("button", { name: "Read records again" });
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/Inspect another record/)).not.toBeInTheDocument();
  });
  it.each(["rescan", "packet", "root", "routes", "stale"])("invalidates retained observations on %s changes even without a new project identity", async kind => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["a.json", "b.json"]));
    vi.mocked(inspectVerificationReceipt).mockImplementation(async (_root, path) => fixture(path));
    const view = show(); await read(); await select("a.json"); await select("b.json");
    const next = structuredClone(snapshotFixture);
    if (kind === "rescan") next.inspection_id = "new-inspection";
    if (kind === "packet") next.state.active_packet!.id = "new-packet";
    if (kind === "root") next.project.root = "/other-root";
    if (kind === "routes") next.state.routed_docs = [...next.state.routed_docs, "new.json"];
    if (kind === "stale") next.inspection_status = "stale";
    view.rerender(<I18nProvider><VerificationRecords snapshot={next} /></I18nProvider>);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/Inspect another record/)).not.toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Selected record" })).not.toBeInTheDocument();
    expect(inspectVerificationReceipt).toHaveBeenCalledTimes(2);
  });
  it("discards retained comparisons and preserves original API error codes after route failure", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["a.json", "b.json"]));
    const error = Object.assign(new Error("Original route revision has changed"), { code: "receipt_navigation_changed" });
    vi.mocked(inspectVerificationReceipt).mockResolvedValueOnce(fixture("a.json")).mockResolvedValueOnce(fixture("b.json")).mockRejectedValueOnce(error);
    show(); await read(); await select("a.json"); await select("b.json");
    fireEvent.click(screen.getByRole("button", { name: "Compare record again" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The record list changed");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("Original error details"));
    expect(screen.getByText(/"code":"receipt_navigation_changed"/)).toBeVisible();
    expect(screen.getByText(/Original route revision has changed/)).toBeVisible();
  });
  it("does not rebuild a comparison from a late observation after routed documents change", async () => {
    let finish!: (value: VerificationReceiptInspection) => void;
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["a.json", "b.json"]));
    vi.mocked(inspectVerificationReceipt).mockResolvedValueOnce(fixture("a.json")).mockReturnValueOnce(new Promise(resolve => { finish = resolve; }));
    const view = show(); await read(); await select("a.json");
    fireEvent.click(screen.getByRole("button", { name: "Inspect record: b.json" }));
    const changed = { ...snapshotFixture, state: { ...snapshotFixture.state, routed_docs: ["different.json"] } };
    view.rerender(<I18nProvider><VerificationRecords snapshot={changed} /></I18nProvider>);
    await act(async () => finish(fixture("b.json")));
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/Inspect another record/)).not.toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Selected record" })).not.toBeInTheDocument();
  });
  it("retains malformed-record errors as unknown in comparison instead of inferring a pass", async () => {
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list(["bad.json", "good.json"]));
    vi.mocked(inspectVerificationReceipt).mockResolvedValueOnce({ ...envelope, observation: { path: "bad.json", receipt: null, source_match: "unknown", log_match: "unknown", sources: [], error: "owner-original unreadable metadata" } })
      .mockResolvedValueOnce(fixture("good.json"));
    show(); await read(); await select("bad.json"); await select("good.json");
    const table = within(screen.getByRole("table"));
    expect(table.getByText("owner-original unreadable metadata")).toBeVisible();
    expect(table.getAllByText("Cannot compare").length).toBeGreaterThan(0);
    expect(table.getAllByText("Command succeeded")).toHaveLength(1);
  });
  it.each(["en", "ko", "ja", "zh-CN"] as const)("explains known reasons in %s and preserves owner text and raw originals", async locale => {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    const copy = verificationCopy[locale];
    vi.mocked(getVerificationReceiptList).mockResolvedValue(list());
    const result = fixture();
    result.observation.sources = [{ path: "src/main.py", match: "changed", reason: "changed_since_run" }, { path: "src/extra.py", match: "unknown", reason: "owner-specific reason: keep this original" }];
    result.observation.receipt!.scope = "Owner scope — 원문";
    result.observation.receipt!.limits = ["Owner limit — leave this verbatim"];
    vi.mocked(inspectVerificationReceipt).mockResolvedValue(result);
    show(); fireEvent.click(screen.getByRole("button", { name: copy.read }));
    fireEvent.click(await screen.findByRole("button", { name: `${copy.inspect}: evidence/run.json` }));
    const article = within(await screen.findByRole("article", { name: copy.selected }));
    fireEvent.click(article.getByText(copy.details));
    expect(article.getByText(copy.reasonChangedSince)).toBeVisible();
    expect(article.getByText(copy.reasonOther)).toBeVisible();
    expect(article.getByText("Owner limit — leave this verbatim")).toBeVisible();
    expect(article.getByText("Owner scope — 원문")).toBeVisible();
    const code = article.getByText("changed_since_run");
    expect(code).not.toBeVisible();
    fireEvent.click(code.closest("details")!.querySelector("summary")!);
    expect(code).toBeVisible();
    const unknown = article.getByText("owner-specific reason: keep this original");
    fireEvent.click(unknown.closest("details")!.querySelector("summary")!);
    expect(unknown).toBeVisible();
    fireEvent.click(article.getByText(copy.rawEvidence));
    expect(article.getByText(/"outcome": "passed"/)).toBeVisible();
  });
  it.each([["ko", "검증 기록 읽기", "수집한 기록 연결하기"], ["ja", "検証記録を読む", "収集した記録をリンク"], ["zh-CN", "读取验证记录", "关联已收集的记录"]])("localizes navigation and connection controls in %s", (locale, label, help) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale); show();
    expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    expect(screen.getByText(help)).toBeInTheDocument();
  });
});
