import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider, useI18n } from "./i18n";

function LocaleProbe() {
  const { locale, t } = useI18n();
  return <div><span>{locale}</span><span>{t("language")}</span><span>{t("rescan")}</span><span>{t("openSdadProject")}</span></div>;
}

function renderProbe(languages: string[]) {
  Object.defineProperty(navigator, "languages", { configurable: true, value: languages });
  return render(<I18nProvider><LocaleProbe /></I18nProvider>);
}

describe("I18nProvider locale detection", () => {
  it("uses the computer Japanese locale on first launch", () => {
    renderProbe(["ja-JP", "en-US"]);
    expect(screen.getByText("ja")).toBeVisible();
    expect(screen.getByText("言語")).toBeVisible();
    expect(screen.getByText("再スキャン")).toBeVisible();
    expect(screen.getByText("SDADプロジェクトを開く")).toBeVisible();
    expect(document.documentElement).toHaveAttribute("lang", "ja");
  });

  it("uses Simplified Chinese for Chinese computer locales", () => {
    renderProbe(["zh-CN", "en-US"]);
    expect(screen.getByText("zh-CN")).toBeVisible();
    expect(screen.getByText("语言")).toBeVisible();
    expect(screen.getByText("重新扫描")).toBeVisible();
    expect(screen.getByText("打开 SDAD 项目")).toBeVisible();
    expect(document.documentElement).toHaveAttribute("lang", "zh-CN");
  });

  it("prefers the cross-launch native preference over origin-local storage", () => {
    document.head.insertAdjacentHTML("beforeend", '<meta name="sdad-locale" content="ja" />');
    window.localStorage.setItem("sdad-inspector:locale:v1", "ko");
    renderProbe(["en-US"]);
    expect(screen.getByText("ja")).toBeVisible();
  });
});
