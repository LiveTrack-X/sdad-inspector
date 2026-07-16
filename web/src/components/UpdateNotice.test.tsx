import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import type { ProductUpdateStatus } from "../types";
import { UPDATE_SUCCESS_NOTICE_MS, UpdateNotice } from "./UpdateNotice";

const updatedStatus: ProductUpdateStatus = {
  supported: true,
  automatic: true,
  current_version: "0.0.3",
  state: "updated",
  available_version: "0.0.3",
  release_url: null,
  downloaded_bytes: 0,
  total_bytes: 0,
  checked_at: "2026-07-16T00:00:00Z",
  message: "updated",
  error: null,
};

function renderNotice(onDismiss: () => void) {
  return render(
    <I18nProvider>
      <UpdateNotice
        status={updatedStatus}
        countdown={null}
        inspectionBusy={false}
        postponed={false}
        onApply={() => undefined}
        onPostpone={() => undefined}
        onRetry={() => undefined}
        onDismiss={onDismiss}
      />
    </I18nProvider>,
  );
}

describe("UpdateNotice", () => {
  afterEach(() => vi.useRealTimers());

  it("automatically dismisses a successful update after the bounded interval", () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    renderNotice(onDismiss);

    act(() => vi.advanceTimersByTime(UPDATE_SUCCESS_NOTICE_MS - 1));
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("offers an accessible immediate dismiss action", () => {
    const onDismiss = vi.fn();
    renderNotice(onDismiss);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss update notification" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
