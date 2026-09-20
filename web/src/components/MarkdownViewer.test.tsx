import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, getDocumentPage } from "../api";
import { I18nProvider } from "../i18n";
import type { DocumentPage, LiveDocument } from "../types";
import { MarkdownViewer } from "./MarkdownViewer";

vi.mock("../api", async (original) => ({ ...await original<typeof import("../api")>(), getDocumentPage: vi.fn() }));
const initial: LiveDocument = { path: "docs/TODO.md", project_root: "C:\\project-a", exists: true, roles: ["todo"], content: "# Preview\nA bounded preview.", sha256: "a".repeat(64), truncated: true, error: null };
function page(start = 1, lines = ["# First page", "Page one content"], changes: Partial<DocumentPage> = {}): DocumentPage {
  return { schema_version: 1, project_root: initial.project_root!, path: initial.path, sha256: initial.sha256!, file_bytes: 9000, file_lines: 620, start, end: start + lines.length - 1, page_bytes: 100, lines, truncated: true, next_start: start + lines.length, heading: null, continuation: "Pin revision", ...changes };
}
const show = (document = initial) => <I18nProvider><MarkdownViewer document={document} navigation /></I18nProvider>;
beforeEach(() => vi.mocked(getDocumentPage).mockReset());

describe("explicit bounded document pages", () => {
  it("reads only on demand and pins next and previous pages to one revision", async () => {
    vi.mocked(getDocumentPage).mockResolvedValueOnce(page()).mockResolvedValueOnce(page(3, ["Page two content"], { next_start: null, truncated: false })).mockResolvedValueOnce(page());
    const user = userEvent.setup();
    render(show());
    expect(screen.getByText("A bounded preview.")).toBeVisible();
    expect(getDocumentPage).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Read by page" }));
    expect(await screen.findByText("Page one content")).toBeVisible();
    expect(getDocumentPage).toHaveBeenNthCalledWith(1, initial.project_root, initial.path, 1, 100, initial.sha256);
    expect(screen.getByText("Lines 1–2 of 620")).toBeVisible();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Page two content")).toBeVisible();
    expect(screen.queryByText("Page one content")).not.toBeInTheDocument();
    expect(getDocumentPage).toHaveBeenNthCalledWith(2, initial.project_root, initial.path, 3, 100, initial.sha256);
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Previous page" }));
    expect(await screen.findByText("Page one content")).toBeVisible();
    expect(getDocumentPage).toHaveBeenNthCalledWith(3, initial.project_root, initial.path, 1, 100, initial.sha256);
    expect(screen.getByText(/does not establish complete work totals/)).toBeVisible();
  });

  it("preserves the old page on source change and requires explicit restart without the old digest", async () => {
    vi.mocked(getDocumentPage).mockResolvedValueOnce(page()).mockRejectedValueOnce(new ApiError("Source changed; inspect current revision", "document_changed")).mockResolvedValueOnce(page(1, ["New revision content"], { sha256: "b".repeat(64) }));
    const user = userEvent.setup();
    render(show());
    await user.click(screen.getByRole("button", { name: "Read by page" }));
    await screen.findByText("Page one content");
    await user.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The document changed");
    expect(screen.getByText("Page one content")).toBeVisible();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Read current version from start" }));
    expect(await screen.findByText("New revision content")).toBeVisible();
    expect(getDocumentPage).toHaveBeenLastCalledWith(initial.project_root, initial.path, 1, 100, undefined);
    expect(screen.queryByText("Page one content")).not.toBeInTheDocument();
  });

  it("ignores late pages from the previous project and does not fetch automatically for a new source", async () => {
    let finish: (value: DocumentPage) => void = () => undefined;
    vi.mocked(getDocumentPage).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const view = render(show());
    await userEvent.setup().click(screen.getByRole("button", { name: "Read by page" }));
    view.rerender(show({ ...initial, project_root: "C:\\project-b", content: "Project B preview" }));
    await act(async () => finish(page()));
    expect(screen.getByText("Project B preview")).toBeVisible();
    expect(screen.queryByText("Page one content")).not.toBeInTheDocument();
    expect(getDocumentPage).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Read by page" })).toBeEnabled();
  });

  it("keeps a page across unchanged refreshes but resets after a source revision changes", async () => {
    vi.mocked(getDocumentPage).mockResolvedValueOnce(page());
    const view = render(show());
    await userEvent.setup().click(screen.getByRole("button", { name: "Read by page" }));
    await screen.findByText("Page one content");
    view.rerender(show({ ...initial, modified_ns: 17 }));
    expect(screen.getByText("Page one content")).toBeVisible();
    view.rerender(show({ ...initial, sha256: "b".repeat(64), content: "New preview" }));
    expect(screen.getByText("New preview")).toBeVisible();
    expect(screen.queryByText("Page one content")).not.toBeInTheDocument();
    expect(getDocumentPage).toHaveBeenCalledTimes(1);
  });

  it("retains preview on a read failure and refuses mismatched returned project identity", async () => {
    vi.mocked(getDocumentPage).mockRejectedValueOnce(new ApiError("Page byte budget exceeded")).mockResolvedValueOnce(page(1, ["Other project page"], { project_root: "C:\\other" }));
    const user = userEvent.setup();
    render(show());
    await user.click(screen.getByRole("button", { name: "Read by page" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Page byte budget exceeded");
    expect(screen.getByText("A bounded preview.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Read by page" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("The document changed"));
    expect(screen.queryByText("Other project page")).not.toBeInTheDocument();
  });

  it.each([["ko", "페이지로 읽기"], ["ja", "ページで読む"], ["zh-CN", "分页阅读"]])("localizes explicit paging in %s", (locale, label) => {
    Object.defineProperty(navigator, "languages", { configurable: true, value: [locale] });
    render(show());
    expect(screen.getByRole("button", { name: label })).toBeVisible();
    expect(getDocumentPage).not.toHaveBeenCalled();
  });
});
