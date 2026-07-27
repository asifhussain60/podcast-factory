/**
 * card-markdown.ts — the card's own markdown, rendered.
 *
 * A Companion note's body is markdown (2026-07-26): the Scholar writes '### '
 * headings, '- ' and '1. ' lists, and light emphasis. This turns that into HTML,
 * and it is the ONE function that does, for both of the things that need it:
 *
 *   the LIVE Session   renders it read-only, with Arabic runs in their own spans
 *   the Composer       seeds the rich-text editor with it, WITHOUT those spans
 *                      (the editor's schema has no such node; the Arabic face is
 *                      applied to the editing surface itself instead)
 *
 * One function, because a reader and an editor that disagree about what a note's
 * markdown means is a note that changes when you open it.
 *
 * A deliberately small subset — headings, both list kinds, paragraphs, blockquote,
 * bold, italic, inline code. It is exactly what the card's toolbar can produce, so
 * the round trip (markdown → editor → markdown) is closed: nothing renders that
 * the editor cannot represent, and nothing the editor writes fails to render.
 *
 * Every scrap of text is escaped. A note body is model output, and it is displayed
 * on a page that also hosts the book's prose.
 */

const ARABIC_RUN = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿][؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿\sً-ْ]*/g;

export interface CardMarkdownOptions {
  /** Wrap Arabic runs in `<span class="xpl-ar">`. Off for the editor seed. */
  arabicSpans?: boolean;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Escape, then wrap Arabic runs. Order matters: the wrapper emits real tags. */
function text(raw: string, opts: CardMarkdownOptions): string {
  const escaped = escapeHtml(raw);
  if (!opts.arabicSpans) return escaped;
  return escaped.replace(ARABIC_RUN, (run) => {
    const trimmed = run.replace(/\s+$/, "");
    const tail = run.slice(trimmed.length);
    return `<span class="xpl-ar" dir="rtl" lang="ar">${trimmed}</span>${tail}`;
  });
}

/** Inline: `**bold**`, `*italic*`, `` `code` ``. Applied after escaping. */
function inline(raw: string, opts: CardMarkdownOptions): string {
  return text(raw, opts)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
}

const HEADING = /^(#{1,6})\s+(.*)$/;
const BULLET = /^\s*[-*]\s+(.*)$/;
const ORDERED = /^\s*(\d+)[.)]\s+(.*)$/;
const QUOTE = /^\s*>\s?(.*)$/;

/**
 * Markdown → HTML for a card body.
 *
 * Heading levels are clamped to h3/h4: a card sits inside a panel that already has
 * a title, and an h1 inside it would out-shout the card it belongs to.
 */
export function cardMarkdownToHtml(
  markdown: string,
  opts: CardMarkdownOptions = {},
): string {
  const lines = String(markdown ?? "")
    .replace(/\r\n?/g, "\n")
    .split("\n");
  const out: string[] = [];
  let para: string[] = [];
  let list: { tag: "ul" | "ol"; items: string[]; start: number } | null = null;
  /** A quotation's PARAGRAPHS, each a list of lines. A blank `> ` line ends a
   *  paragraph and keeps the quotation open — which is what makes a verse, its
   *  rendering and its citation three lines rather than one run-on. */
  let quote: string[][] = [];

  const flushPara = () => {
    if (!para.length) return;
    out.push(`<p>${inline(para.join(" "), opts)}</p>`);
    para = [];
  };
  const flushList = () => {
    if (!list) return;
    const start =
      list.tag === "ol" && list.start !== 1 ? ` start="${list.start}"` : "";
    out.push(
      `<${list.tag}${start}>${list.items.map((i) => `<li><p>${inline(i, opts)}</p></li>`).join("")}</${list.tag}>`,
    );
    list = null;
  };
  const flushQuote = () => {
    const paras = quote.map((lines) => lines.join(" ").trim()).filter(Boolean);
    quote = [];
    if (!paras.length) return;
    out.push(
      `<blockquote>${paras.map((p) => `<p>${inline(p, opts)}</p>`).join("")}</blockquote>`,
    );
  };
  const flushAll = () => {
    flushPara();
    flushList();
    flushQuote();
  };

  for (const line of lines) {
    if (!line.trim()) {
      flushAll();
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) {
      flushAll();
      const level = Math.min(4, Math.max(3, heading[1].length));
      out.push(`<h${level}>${inline(heading[2], opts)}</h${level}>`);
      continue;
    }
    const bullet = BULLET.exec(line);
    if (bullet) {
      flushPara();
      flushQuote();
      if (list?.tag !== "ul") {
        flushList();
        list = { tag: "ul", items: [], start: 1 };
      }
      list.items.push(bullet[1]);
      continue;
    }
    const ordered = ORDERED.exec(line);
    if (ordered) {
      flushPara();
      flushQuote();
      if (list?.tag !== "ol") {
        flushList();
        list = { tag: "ol", items: [], start: Number(ordered[1]) || 1 };
      }
      list.items.push(ordered[2]);
      continue;
    }
    const q = QUOTE.exec(line);
    if (q) {
      flushPara();
      flushList();
      const content = q[1].trim();
      if (!content)
        quote.push([]); // blank quote line: next paragraph
      else if (quote.length) quote[quote.length - 1].push(content);
      else quote.push([content]);
      continue;
    }
    // A continuation line inside a list item belongs to that item, not to a new
    // paragraph that would break the list in two.
    if (list) {
      list.items[list.items.length - 1] += ` ${line.trim()}`;
      continue;
    }
    flushQuote();
    para.push(line.trim());
  }
  flushAll();
  return out.join("");
}
