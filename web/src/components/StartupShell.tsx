import { Minus, Moon, Plus, Sun, Translate as TranslateIcon } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import { type Locale, LOCALE_OPTIONS, useI18n } from "../i18n";
import type { Theme } from "../theme";
import { DEFAULT_UI_SCALE } from "../uiScale";

const REPOSITORY_URL = "https://github.com/LiveTrack-X/sdad-inspector";

interface Props {
  children: ReactNode;
  theme: Theme;
  onToggleTheme: () => void;
  uiScale: number;
  onDecreaseUiScale: () => void;
  onIncreaseUiScale: () => void;
  onResetUiScale: () => void;
  onOpenRepository: () => void;
}

export function StartupShell({ children, theme, onToggleTheme, uiScale, onDecreaseUiScale, onIncreaseUiScale, onResetUiScale, onOpenRepository }: Props) {
  const { locale, setLocale, t } = useI18n();
  return (
    <div className="app-shell startup-shell">
      <header className="command-bar startup-command-bar">
        <div className="brand" aria-label="SDAD Inspector"><span className="brand-mark"><img src="/sdad-inspector-logo.png" alt="" /></span><span className="brand-name">SDAD Inspector</span></div>
        <div className="command-actions">
          <div className="startup-scale-control" role="group" aria-label={t("uiScale")}>
            <button onClick={onDecreaseUiScale} disabled={uiScale <= 90} aria-label={t("decreaseUiScale")}><Minus size={16} /></button>
            <button className="scale-value" onClick={onResetUiScale} title={t("resetUiScale", { scale: DEFAULT_UI_SCALE })}>{uiScale}%</button>
            <button onClick={onIncreaseUiScale} disabled={uiScale >= 150} aria-label={t("increaseUiScale")}><Plus size={16} /></button>
          </div>
          <label className="language-select" title={t("language")}><TranslateIcon size={17} /><span className="sr-only">{t("language")}</span><select aria-label={t("language")} value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>{LOCALE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{t(option.labelKey)}</option>)}</select></label>
          <button className="icon-button theme-toggle" onClick={onToggleTheme} aria-label={theme === "dark" ? t("useLightTheme") : t("useDarkTheme")} title={theme === "dark" ? t("useLightTheme") : t("useDarkTheme")}>{theme === "dark" ? <Sun size={19} /> : <Moon size={19} />}</button>
        </div>
      </header>
      <main className="startup-workspace">
        <img src="/sdad-inspector-logo.png" alt="" />
        <h1>{t("chooseProjectToBegin")}</h1>
        <p>{t("chooseProjectToBeginDetail")}</p>
      </main>
      <footer className="startup-status-bar"><a href={REPOSITORY_URL} target="_blank" rel="noreferrer" onClick={(event) => { event.preventDefault(); onOpenRepository(); }} aria-label={t("openProductRepository")}>{t("createdByLiveTrack")}</a></footer>
      {children}
    </div>
  );
}
