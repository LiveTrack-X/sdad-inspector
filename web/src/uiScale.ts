import { useCallback, useEffect, useState } from "react";
import { updateUiPreferences } from "./api";

export const UI_SCALE_STORAGE_KEY = "sdad-inspector:ui-scale:v1";
export const DEFAULT_UI_SCALE = 110;
export const MIN_UI_SCALE = 90;
export const MAX_UI_SCALE = 150;
const UI_SCALE_STEP = 10;

function normalizeUiScale(value: string | number | null | undefined): number | null {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(parsed) || parsed < MIN_UI_SCALE || parsed > MAX_UI_SCALE || parsed % UI_SCALE_STEP !== 0) return null;
  return parsed;
}

function initialUiScale(): number {
  const nativePreference = document.querySelector<HTMLMetaElement>('meta[name="sdad-ui-scale"]')?.content;
  const nativeScale = normalizeUiScale(nativePreference);
  if (nativeScale !== null) return nativeScale;
  try {
    return normalizeUiScale(window.localStorage.getItem(UI_SCALE_STORAGE_KEY)) ?? DEFAULT_UI_SCALE;
  } catch {
    return DEFAULT_UI_SCALE;
  }
}

export function useUiScale() {
  const [scale, setScaleState] = useState(initialUiScale);

  useEffect(() => {
    const factor = scale / 100;
    document.body.style.setProperty("zoom", String(factor));
    // Chromium/WebView adjusts the horizontal CSS viewport for `zoom`; a width
    // compensation shrinks the usable layout and clips the command bar.
    document.body.style.removeProperty("width");
    // The `100vh` body minimum is not adjusted in the same way, so compensate
    // only the vertical dimensions to keep the status bar inside the viewport.
    document.body.style.height = `${100 / factor}%`;
    document.body.style.minHeight = `${100 / factor}vh`;
    document.documentElement.dataset.uiScale = String(scale);
  }, [scale]);

  const setScale = useCallback((next: number) => {
    const normalized = normalizeUiScale(next);
    if (normalized === null) return;
    setScaleState(normalized);
    try {
      window.localStorage.setItem(UI_SCALE_STORAGE_KEY, String(normalized));
    } catch {
      // The active session still changes scale when storage is unavailable.
    }
    void updateUiPreferences({ scale: normalized }).catch(() => undefined);
  }, []);

  const increaseScale = useCallback(() => setScale(Math.min(MAX_UI_SCALE, scale + UI_SCALE_STEP)), [scale, setScale]);
  const decreaseScale = useCallback(() => setScale(Math.max(MIN_UI_SCALE, scale - UI_SCALE_STEP)), [scale, setScale]);
  const resetScale = useCallback(() => setScale(DEFAULT_UI_SCALE), [setScale]);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
      if (["+", "="].includes(event.key)) {
        event.preventDefault(); increaseScale();
      } else if (event.key === "-") {
        event.preventDefault(); decreaseScale();
      } else if (event.key === "0") {
        event.preventDefault(); resetScale();
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [decreaseScale, increaseScale, resetScale]);

  return { scale, increaseScale, decreaseScale, resetScale };
}
