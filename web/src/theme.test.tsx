import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { THEME_STORAGE_KEY, useTheme } from "./theme";

function ThemeProbe() {
  const { theme, toggleTheme } = useTheme();
  return <button onClick={toggleTheme}>{theme}</button>;
}

describe("useTheme", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("restores the app-data preference across changing loopback origins", async () => {
    document.head.insertAdjacentHTML("beforeend", '<meta name="sdad-theme" content="dark" />');
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ schema_version: 1, theme: "light", locale: null, scale: null }), { headers: { "Content-Type": "application/json" } })));
    render(<ThemeProbe />);

    expect(screen.getByRole("button", { name: "dark" })).toBeVisible();
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    fireEvent.click(screen.getByRole("button", { name: "dark" }));
    expect(screen.getByRole("button", { name: "light" })).toBeVisible();
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/preferences", expect.objectContaining({ method: "POST" })));
  });
});
