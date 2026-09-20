import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getVerificationReceiptList, inspectVerificationReceipt, revealPath } from "../api";
import { I18nProvider, LOCALE_STORAGE_KEY } from "../i18n";
import { snapshotFixture } from "../test/fixture";
import type { VerificationReceiptInspection, VerificationReceiptList } from "../verificationReceipts";
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
    expect(screen.getByText("Command succeeded")).toBeInTheDocument();
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
  it.each([["ko", "검증 기록 읽기", "수집한 기록 연결하기"], ["ja", "検証記録を読む", "収集した記録をリンク"], ["zh-CN", "读取验证记录", "关联已收集的记录"]])("localizes navigation and connection controls in %s", (locale, label, help) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale); show();
    expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    expect(screen.getByText(help)).toBeInTheDocument();
  });
});
