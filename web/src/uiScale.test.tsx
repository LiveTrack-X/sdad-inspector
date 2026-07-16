import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { UI_SCALE_STORAGE_KEY, useUiScale } from "./uiScale";

function ScaleProbe() {
  const { scale, increaseScale, decreaseScale, resetScale } = useUiScale();
  return <div><output>{scale}%</output><button onClick={decreaseScale}>minus</button><button onClick={increaseScale}>plus</button><button onClick={resetScale}>reset</button></div>;
}

describe("useUiScale", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("restores, changes, and persists whole-UI scaling", async () => {
    document.head.insertAdjacentHTML("beforeend", '<meta name="sdad-ui-scale" content="130" />');
    window.localStorage.setItem(UI_SCALE_STORAGE_KEY, "90");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ schema_version: 1, theme: null, locale: null, scale: 140 }), { headers: { "Content-Type": "application/json" } })));
    render(<ScaleProbe />);

    expect(screen.getByText("130%")).toBeVisible();
    expect(document.documentElement).toHaveAttribute("data-ui-scale", "130");
    expect(document.body.style.zoom).toBe("1.3");
    expect(document.body.style.width).toBe("");
    expect(document.body.style.height).not.toBe("");
    expect(document.body.style.minHeight).not.toBe("");
    fireEvent.click(screen.getByRole("button", { name: "plus" }));
    expect(screen.getByText("140%")).toBeVisible();
    expect(window.localStorage.getItem(UI_SCALE_STORAGE_KEY)).toBe("140");
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/preferences", expect.objectContaining({ method: "POST" })));
  });

  it("supports standard reset and zoom keyboard shortcuts", () => {
    render(<ScaleProbe />);
    fireEvent.keyDown(window, { key: "+", ctrlKey: true });
    expect(screen.getByText("120%")).toBeVisible();
    fireEvent.keyDown(window, { key: "0", ctrlKey: true });
    expect(screen.getByText("110%")).toBeVisible();
    fireEvent.keyDown(window, { key: "-", ctrlKey: true });
    expect(screen.getByText("100%")).toBeVisible();
  });
});
