import { Fragment, createElement, type ReactNode, useEffect, useId, useMemo, useRef, useState } from "react";
import { ArrowSquareOut, CheckSquare, Image, Info, ListBullets, Square } from "@phosphor-icons/react";
import { type Translate, useI18n } from "../i18n";
import { ApiError, getDocumentPage } from "../api";
import { documentPageCopy } from "../documentPageCopy";
import type { DocumentPage, LiveDocument } from "../types";
import "./documentPages.css";

interface MarkdownHeading {
  id: string;
  label: string;
  level: number;
  line: number;
}

function safeLink(href: string): string | null {
  if (/^https?:\/\//i.test(href) || /^mailto:/i.test(href)) return href;
  return null;
}

function safeImageLink(href: string): string | null {
  return /^https?:\/\//i.test(href) ? href : null;
}

function inline(text: string, keyPrefix: string, t: Translate): ReactNode[] {
  const pattern = /(!\[[^\]]*\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\[[^\]]+\]\([^)]+\)|\*[^*]+\*|_[^_]+_)/g;
  const result: ReactNode[] = [];
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > cursor) result.push(text.slice(cursor, index));
    const token = match[0];
    const key = `${keyPrefix}-${index}`;
    if (token.startsWith("![")) {
      const image = token.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      const alt = image?.[1].trim() || t("markdownImage");
      const href = image ? safeImageLink(image[2].trim()) : null;
      result.push(
        <span className="markdown-image-fallback" role="group" aria-label={alt} key={key}>
          <Image size={17} aria-hidden="true" />
          <span>{alt}</span>
          {href
            ? <a href={href} target="_blank" rel="noreferrer"><ArrowSquareOut size={14} aria-hidden="true" />{t("openImageLink")}</a>
            : <em>{t("imageNotDisplayed")}</em>}
        </span>,
      );
    } else if (token.startsWith("`")) result.push(<code key={key}>{token.slice(1, -1)}</code>);
    else if (token.startsWith("**") || token.startsWith("__")) result.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    else if (token.startsWith("[")) {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      const href = link ? safeLink(link[2].trim()) : null;
      result.push(href ? <a key={key} href={href} target="_blank" rel="noreferrer">{link?.[1]}</a> : <span key={key}>{link?.[1] ?? token}</span>);
    } else result.push(<em key={key}>{token.slice(1, -1)}</em>);
    cursor = index + token.length;
  }
  if (cursor < text.length) result.push(text.slice(cursor));
  return result;
}

function isBlockStart(lines: string[], index: number): boolean {
  const line = lines[index] ?? "";
  return /^#{1,6}\s/.test(line) || /^```/.test(line) || /^>\s?/.test(line)
    || /^[-*+]\s/.test(line) || /^\d+\.\s/.test(line) || /^---+$/.test(line)
    || (line.includes("|") && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1] ?? ""));
}

function headingLabel(value: string): string {
  return value
    .replace(/!?\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .trim();
}

function extractHeadings(markdown: string, prefix: string): MarkdownHeading[] {
  return markdown.split(/\r?\n/).flatMap((line, index) => {
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (!heading) return [];
    return [{
      id: `${prefix}-heading-${index}`,
      label: headingLabel(heading[2]),
      level: heading[1].length,
      line: index,
    }];
  });
}

function renderMarkdown(markdown: string, headingIds: ReadonlyMap<number, string>, t: Translate): ReactNode[] {
  const lines = markdown.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const children = inline(heading[2], `h-${index}`, t);
      const id = headingIds.get(index);
      const tag = `h${level}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
      blocks.push(createElement(tag, { key: index, id, tabIndex: id ? -1 : undefined }, children));
      index += 1; continue;
    }
    if (/^```/.test(line)) {
      const language = line.slice(3).trim();
      const code: string[] = [];
      index += 1;
      while (index < lines.length && !/^```/.test(lines[index])) code.push(lines[index++]);
      if (index < lines.length) index += 1;
      blocks.push(<pre key={`code-${index}`}><code data-language={language || undefined}>{code.join("\n")}</code></pre>);
      continue;
    }
    if (/^---+$/.test(line.trim())) { blocks.push(<hr key={index} />); index += 1; continue; }
    if (line.includes("|") && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1] ?? "")) {
      const headers = line.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        rows.push(lines[index].replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim())); index += 1;
      }
      blocks.push(<div className="markdown-table-wrap" key={`table-${index}`}><table><thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex}>{inline(cell, `th-${index}-${cellIndex}`, t)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{inline(cell, `td-${index}-${rowIndex}-${cellIndex}`, t)}</td>)}</tr>)}</tbody></table></div>);
      continue;
    }
    if (/^>\s?/.test(line)) {
      const quote: string[] = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) quote.push(lines[index++].replace(/^>\s?/, ""));
      blocks.push(<blockquote key={`quote-${index}`}>{quote.map((item, itemIndex) => <Fragment key={itemIndex}>{inline(item, `q-${index}-${itemIndex}`, t)}{itemIndex < quote.length - 1 && <br />}</Fragment>)}</blockquote>);
      continue;
    }
    if (/^[-*+]\s/.test(line)) {
      const items: Array<{ text: string; checked: boolean | null }> = [];
      while (index < lines.length && /^[-*+]\s/.test(lines[index])) {
        const raw = lines[index].replace(/^[-*+]\s/, "");
        const task = raw.match(/^\[([ xX])\]\s+(.*)$/);
        items.push({ text: task ? task[2] : raw, checked: task ? task[1].toLocaleLowerCase() === "x" : null });
        index += 1;
        while (index < lines.length && /^\s{2,}\S/.test(lines[index]) && !/^\s*[-*+]\s/.test(lines[index])) {
          items[items.length - 1].text += ` ${lines[index].trim()}`; index += 1;
        }
      }
      blocks.push(<ul key={`ul-${index}`} className={items.some((item) => item.checked !== null) ? "task-list" : undefined}>{items.map((item, itemIndex) => <li key={itemIndex}>{item.checked !== null && <span className={`task-box ${item.checked ? "checked" : ""}`}>{item.checked ? <CheckSquare weight="fill" /> : <Square />}</span>}<span>{inline(item.text, `li-${index}-${itemIndex}`, t)}</span></li>)}</ul>);
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\.\s/.test(lines[index])) items.push(lines[index++].replace(/^\d+\.\s/, ""));
      blocks.push(<ol key={`ol-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inline(item, `ol-${index}-${itemIndex}`, t)}</li>)}</ol>);
      continue;
    }
    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines, index)) paragraph.push(lines[index++].trim());
    blocks.push(<p key={`p-${index}`}>{inline(paragraph.join(" "), `p-${index}`, t)}</p>);
  }
  return blocks;
}

export function MarkdownViewer({ document: liveDocument, navigation = false }: { document: LiveDocument; navigation?: boolean }) {
  const { t, locale } = useI18n();
  const copy = documentPageCopy(locale);
  const sourceKey = JSON.stringify([liveDocument.project_root, liveDocument.path, liveDocument.sha256 ?? liveDocument.content]);
  const latestKey = useRef(sourceKey);
  latestKey.current = sourceKey;
  const serial = useRef(0);
  const [paging, setPaging] = useState<{ key: string; page: DocumentPage; previous: number[] } | null>(null);
  const [requestState, setRequestState] = useState<{ key: string; busy: boolean; error: string | null; changed: boolean } | null>(null);
  const current = paging?.key === sourceKey ? paging : null;
  const request = requestState?.key === sourceKey ? requestState : null;
  useEffect(() => () => { serial.current += 1; }, []);
  const headingPrefix = useId().replaceAll(":", "");
  const content = current ? current.page.lines.join("\n") : liveDocument.content ?? "";
  const headings = useMemo(
    () => navigation ? extractHeadings(content, headingPrefix) : [],
    [content, headingPrefix, navigation],
  );
  const headingIds = useMemo(
    () => new Map(headings.map((heading) => [heading.line, heading.id])),
    [headings],
  );
  const rendered = useMemo(() => renderMarkdown(content, headingIds, t), [content, headingIds, t]);

  async function readPage(start: number, digest: string | undefined, previous: number[]) {
    if (!liveDocument.project_root || request?.busy) return;
    const key = sourceKey;
    const call = ++serial.current;
    setRequestState({ key, busy: true, error: null, changed: false });
    try {
      const page = await getDocumentPage(liveDocument.project_root, liveDocument.path, start, 100, digest);
      if (call !== serial.current || latestKey.current !== key) return;
      if (page.project_root !== liveDocument.project_root || page.path !== liveDocument.path.replaceAll("\\", "/") || (digest && page.sha256 !== digest)) {
        throw new ApiError("The returned page does not match the selected source.", "document_changed");
      }
      setPaging({ key, page, previous });
      setRequestState({ key, busy: false, error: null, changed: false });
    } catch (error) {
      if (call !== serial.current || latestKey.current !== key) return;
      setRequestState({ key, busy: false, error: error instanceof Error ? error.message : copy.unavailable, changed: error instanceof ApiError && error.code === "document_changed" });
    }
  }

  function jumpToHeading(id: string) {
    if (!id) return;
    const target = globalThis.document?.getElementById(id);
    if (!target) return;
    target.focus({ preventScroll: true });
    const reducedMotion = typeof window !== "undefined"
      && typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView?.({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  }

  if (liveDocument.error) return <div className="document-error" role="alert"><strong>{liveDocument.error.code}</strong><p>{liveDocument.error.message}</p></div>;
  if (!liveDocument.exists || liveDocument.content === null) return <div className="document-empty">{t("documentUnavailable")}</div>;
  return (
    <>
      {liveDocument.truncated && !current && (
        <div className="document-preview-note" role="note">
          <Info size={18} />
          <p>{liveDocument.project_root ? copy.preview : t("documentPreviewTruncated")}</p>
        </div>
      )}
      {liveDocument.project_root && (liveDocument.truncated || current) && (
        <nav className="document-page-controls" aria-label={copy.title}>
          <div className="document-page-actions">
            {!current && <button disabled={request?.busy || request?.changed} onClick={() => void readPage(1, liveDocument.sha256, [])}>{copy.read}</button>}
            {current && <>
              <button disabled={request?.busy || request?.changed || !current.previous.length} onClick={() => void readPage(current.previous[current.previous.length - 1], current.page.sha256, current.previous.slice(0, -1))}>{copy.previous}</button>
              <button disabled={request?.busy || request?.changed || current.page.next_start === null} onClick={() => void readPage(current.page.next_start!, current.page.sha256, [...current.previous, current.page.start])}>{copy.next}</button>
            </>}
            {(current || request?.error) && <button disabled={request?.busy} onClick={() => void readPage(1, undefined, [])}>{copy.restart}</button>}
          </div>
          {request?.busy && <p role="status">{copy.loading}</p>}
          {request?.error && <div className="document-page-error" role="alert"><p>{request.changed ? copy.changed : copy.unavailable}</p>{!request.changed && <p>{request.error}</p>}</div>}
          {current && <><p>{copy.range.replace("{start}", String(current.page.file_lines ? current.page.start : 0)).replace("{end}", String(current.page.end)).replace("{total}", String(current.page.file_lines))}</p><code>SHA-256 {current.page.sha256}</code><p>{copy.fragment}</p></>}
        </nav>
      )}
      {navigation && headings.length > 0 && (
        <div className="markdown-navigation">
          <ListBullets size={18} />
          <label>
            <span>{t("documentOutline")}</span>
            <select
              aria-label={t("documentOutline")}
              defaultValue=""
              onChange={(event) => {
                jumpToHeading(event.currentTarget.value);
                event.currentTarget.value = "";
              }}
            >
              <option value="">{t("jumpToHeading")}</option>
              {headings.map((heading) => (
                <option key={heading.id} value={heading.id}>
                  {`${"— ".repeat(Math.max(0, heading.level - 1))}${heading.label}`}
                </option>
              ))}
            </select>
          </label>
          <span className="markdown-heading-count">{t("documentHeadingCount", { count: headings.length })}</span>
        </div>
      )}
      <article className="markdown-viewer">{rendered}</article>
    </>
  );
}
