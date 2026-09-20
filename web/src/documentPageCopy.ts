import type { Locale } from "./i18n";

const en = {
  title: "Document pages", read: "Read by page", previous: "Previous page", next: "Next page", restart: "Read current version from start",
  loading: "Reading selected page…", range: "Lines {start}–{end} of {total}",
  preview: "This is a bounded preview. Use document pages to read further within the reader's file and page limits.",
  fragment: "Only this page is shown. Formatting and the outline may depend on context outside this page; this does not establish complete work totals.",
  changed: "The document changed. The previous page is retained; restart to read the current version.",
  unavailable: "This page could not be read. The previous content is retained.",
};
const translations: Record<Locale, typeof en> = {
  en,
  ko: { title: "문서 페이지", read: "페이지로 읽기", previous: "이전 페이지", next: "다음 페이지", restart: "현재 버전을 처음부터 읽기", loading: "선택한 페이지를 읽는 중…", range: "전체 {total}줄 중 {start}–{end}줄", preview: "제한된 미리보기입니다. 문서 페이지 기능으로 파일·페이지 읽기 한도 안에서 이어서 읽을 수 있습니다.", fragment: "이 페이지만 표시합니다. 서식과 목차는 앞뒤 문맥에 따라 달라질 수 있으며, 전체 작업 수를 확인한 것은 아닙니다.", changed: "문서가 변경되었습니다. 이전 페이지를 보존했습니다. 현재 버전을 처음부터 다시 읽으세요.", unavailable: "이 페이지를 읽지 못했습니다. 이전 내용을 보존했습니다." },
  ja: { title: "文書ページ", read: "ページで読む", previous: "前のページ", next: "次のページ", restart: "現在の版を最初から読む", loading: "選択したページを読み込み中…", range: "全{total}行の{start}–{end}行", preview: "制限付きプレビューです。文書ページからファイルとページの読み取り上限内で続きを読めます。", fragment: "このページのみを表示します。書式や目次は前後の文脈に依存する場合があり、作業総数の確認を意味しません。", changed: "文書が変更されました。前のページは保持されています。現在の版を最初から読み直してください。", unavailable: "このページを読み込めませんでした。前の内容は保持されています。" },
  "zh-CN": { title: "文档分页", read: "分页阅读", previous: "上一页", next: "下一页", restart: "从头读取当前版本", loading: "正在读取所选页面…", range: "共{total}行，第{start}–{end}行", preview: "这是受限预览。可在文件及页面读取限制内通过分页继续阅读。", fragment: "仅显示当前页面。格式和目录可能依赖前后文，这不代表已确认全部工作数量。", changed: "文档已更改。已保留上一页，请从头读取当前版本。", unavailable: "无法读取此页，已保留之前的内容。" },
};
export function documentPageCopy(locale: Locale) { return translations[locale]; }
