import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { doctorResult } from "../doctorResult";
import { I18nProvider } from "../i18n";
import { selectionFor } from "../selection";
import { liveDocumentsFixture, snapshotFixture } from "../test/fixture";
import type { Snapshot } from "../types";
import { Overview } from "./Overview";
import { RepositoryTree } from "./RepositoryTree";

vi.mock("./InteractionPanel", () => ({ InteractionPanel: () => null }));

const unavailableCases: [string, (snapshot: Snapshot) => void][] = [
  ["stale inspection", (snapshot) => { snapshot.inspection_status = "stale"; }],
  ["diagnostic inspection", (snapshot) => { snapshot.inspection_status = "diagnostic"; }],
  ["incomplete Doctor", (snapshot) => { snapshot.doctor.completed = false; }],
  ["diagnostic error", (snapshot) => { snapshot.doctor.diagnostic_error = { kind: "failed", message: "Doctor timed out" }; }],
  ["changed control files", (snapshot) => { snapshot.integrity.control_files_unchanged_during_inspection = false; }],
  ["unexpected exit code", (snapshot) => { snapshot.doctor.exit_code = 2; }],
];

function surface(snapshot: Snapshot, selectedId = "overview") {
  return <I18nProvider>
    <RepositoryTree snapshot={snapshot} selectedId={selectedId} onSelect={vi.fn()} mobileOpen={false} onCloseMobile={vi.fn()} activity={null} packetWork={[]} packetWorkComplete={true} rule5={null}/>
    <Overview snapshot={snapshot} selectedId={selectedId} selection={selectionFor(snapshot, selectedId, (key) => key)} busy={false} progress={null} onSelect={vi.fn()} liveDocuments={liveDocumentsFixture} activity={null} packetWork={[]} rule5={null}/>
  </I18nProvider>;
}

describe("Doctor observation boundaries", () => {
  it.each(unavailableCases)("does not turn %s into zero findings or a successful check", (_name, change) => {
    const snapshot = structuredClone(snapshotFixture);
    change(snapshot);
    expect(doctorResult(snapshot)).toEqual({ available: false, passed: false });
    const view = render(surface(snapshot));
    const summary = document.querySelector(".doctor-summary")!;
    expect(within(summary as HTMLElement).getByText(/current, complete Doctor result is unavailable/)).toBeVisible();
    expect(summary.querySelector(".doctor-counts.success")).toBeNull();
    expect(within(summary as HTMLElement).queryByText("0 errors")).not.toBeInTheDocument();
    const node = screen.getByRole("treeitem", { name: /Review Findings/ });
    expect(node).toHaveTextContent(/unavailable/i);
    expect(node.querySelector(".success")).toBeNull();
    expect(screen.getByRole("treeitem", { name: /^Errors\s*—$/ })).toBeVisible();

    view.rerender(surface(snapshot, "findings"));
    expect(screen.queryByText("No finding exists for this selection.")).not.toBeInTheDocument();
    const strip = screen.getByLabelText("Doctor findings");
    expect([...strip.querySelectorAll("strong")].map((item) => item.textContent)).toEqual(["—", "—", "—"]);
    for (const id of ["findings", "findings-errors", "findings-warnings", "findings-notes"]) {
      const selection = selectionFor(snapshot, id, (key) => key);
      expect(selection.observed).toBe("unavailable");
      expect(selection.remediation).toBe("doctorResultUnavailable");
    }
    if (snapshot.doctor.diagnostic_error) expect(screen.getByText("Doctor timed out")).toBeVisible();
  });

  it("limits a current clean result to structural checks without claiming declared validation execution", () => {
    render(surface(snapshotFixture));
    expect(doctorResult(snapshotFixture)).toEqual({ available: true, passed: true });
    expect(screen.getByText("0 errors")).toBeVisible();
    expect(screen.getByText(/Doctor found no errors or warnings in structural checks. Declared validation commands were not executed/)).toBeVisible();
    expect(document.querySelector(".doctor-counts.success")).not.toBeNull();
    expect(snapshotFixture.state.validation.every((validation) => validation.executed === false)).toBe(true);
  });

  it("does not mark a completed nonzero exit successful even with zero reported findings", () => {
    const snapshot = structuredClone(snapshotFixture);
    snapshot.doctor.exit_code = 1;
    expect(doctorResult(snapshot)).toEqual({ available: true, passed: false });
    const view = render(surface(snapshot));
    expect(screen.getByText("0 errors")).toBeVisible();
    expect(screen.getByText(/Doctor did not pass/)).toBeVisible();
    expect(document.querySelector(".doctor-counts.success")).toBeNull();
    expect(screen.getByRole("treeitem", { name: /Review Findings/ }).querySelector(".success")).toBeNull();
    view.rerender(surface(snapshot, "findings"));
    expect(screen.queryByText("No finding exists for this selection.")).not.toBeInTheDocument();
    expect(selectionFor(snapshot, "findings", (key) => key).remediation).toBe("doctorUnsuccessful");
  });

  it("retains stale findings as evidence while withholding a current count", () => {
    const snapshot = structuredClone(snapshotFixture);
    snapshot.inspection_status = "stale";
    snapshot.doctor.findings = [{ id: "state.old", severity: "error", path: "sdad-state.yaml", line: null, message: "Previously observed error", evidence: "old observation", remediation: "Recheck current state" }];
    render(surface(snapshot, "findings"));
    expect(screen.getByText("Previously observed error")).toBeVisible();
    expect(screen.getByText(/current, complete Doctor result is unavailable/)).toBeVisible();
  });
});
