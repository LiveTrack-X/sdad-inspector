import { useCallback, useEffect, useState } from "react";
import { updateUiPreferences } from "./api";

export type Theme = "light" | "dark";
export const THEME_STORAGE_KEY = "sdad-inspector:theme:v1";

function initialTheme(): Theme {
  const nativePreference = document.querySelector<HTMLMetaElement>('meta[name="sdad-theme"]')?.content;
  if (nativePreference === "light" || nativePreference === "dark") return nativePreference;
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // A session theme still works when browser storage is unavailable.
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // The active session still changes theme when storage is unavailable.
    }
    void updateUiPreferences({ theme: next }).catch(() => undefined);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [setTheme, theme]);

  return { theme, setTheme, toggleTheme };
}
