/**
 * Minimal markdown → HTML converter for podcast-factory prose content — the
 * ONE renderer behind both surfaces (R2 of the clean-code hardening plan
 * merged the former source-render.ts into this module):
 *
 *   - Book/chapter prose (default options): paragraphs, headers with anchor
 *     ids, bold/italic/inline code, links, ul/ol lists, Arabic-aware
 *     blockquotes (.ar/.tr + `quran` class), md-comment divs.
 *   - Source-extractor bundles (`renderSourceMarkdown`): ⟪ar:…⟫ / ⟪ar-quote:…⟫
 *     inline Arabic + ⟪quran X:Y⟫ citation chips, section-comment dividers,
 *     pipe tables, [diagram]/[image] blocks — no heading ids, no lists, no
 *     transliteration folding.
 *
 * We don't need full CommonMark, and shipping a dependency that does is
 * overkill. IMPORTANT: emphasis spans are preserved as `<em>`/`<strong>` so
 * the highlight-renderer can wrap them in ref-category spans without
 * re-parsing.
 */

import { simplifyTransliteration } from "../translit";

/** Arabic-script detection (matches the print renderer's ARABIC_RE). */
const ARABIC_SCRIPT_RE = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/;

export interface RenderOptions {
  /** Add slug ids to headings for in-chapter anchoring. Default true. */
  headingIds?: boolean;
  /** Parse `-`/`*`/`+` and `1.` lists. Default true. */
  lists?: boolean;
  /** Parse pipe tables (header + separator + body). Default false. */
  tables?: boolean;
  /** Parse ⟪ar:…⟫ / ⟪quran X:Y⟫ inline markers; disables code/links. Default false. */
  angleMarkers?: boolean;
  /** Render `<!-- section N (id=…) -->` comments as .se-section-marker dividers. Default false. */
  sectionMarkers?: boolean;
  /** Tag Arabic blockquote lines .ar/.tr + `quran` class. Default true. */
  arabicBlockquotes?: boolean;
  /** Render [diagram:…]/[image:…] lines as .se-image-block paragraphs. Default false. */
  imageBlocks?: boolean;
  /** Fold scholarly transliteration to plain English first. Default true. */
  simplifyTranslit?: boolean;
}

/** The source-extractor bundle profile (the former source-render.ts). */
const SOURCE_PROFILE: RenderOptions = {
  headingIds: false,
  lists: false,
  tables: true,
  angleMarkers: true,
  sectionMarkers: true,
  arabicBlockquotes: false,
  imageBlocks: true,
  simplifyTranslit: false,
};

function escapeHtml(s: string): string {
  // Don't escape apostrophes — they're safe in HTML text content and inside
  // double-quoted attributes. Escaping them as &#39; breaks downstream
  // pattern matching (e.g. "Abu Ya'qub" → "Abu Ya&#39;qub" which the Arabic
  // detector can't see through). Only escape what's actually unsafe.
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** ⟪…⟫ marker pass: escape text OUTSIDE markers, emit marker tags directly. */
function renderAngleMarkers(text: string): string {
  const markerRe = /⟪([a-z-]+):([^⟪⟫]*)⟫|⟪quran (\d+):(\d+)(?:-(\d+))?⟫/g;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = markerRe.exec(text)) !== null) {
    out += escapeHtml(text.slice(last, m.index));
    if (m[3] !== undefined) {
      const surah = m[3];
      const start = m[4];
      const end = m[5];
      const ref = end
        ? `Quran ${surah}:${start}–${end}`
        : `Quran ${surah}:${start}`;
      out += `<span class="quran-cite" dir="ltr">${ref}</span>`;
    } else {
      const kind = m[1]; // "ar", "ar-quote", or arbitrary "ar-*"
      const cls = kind === "ar-quote" ? "ar-quote" : "ar";
      const trimmed = m[2].trim();
      out += `<span class="${cls}" lang="ar" dir="rtl">${escapeHtml(trimmed)}</span>`;
    }
    last = m.index + m[0].length;
  }
  return out + escapeHtml(text.slice(last));
}

function renderInline(text: string, opts: RenderOptions): string {
  let s: string;
  if (opts.angleMarkers) {
    // Source flavor: markers first (escaping around them), then emphasis only.
    s = renderAngleMarkers(text);
  } else {
    s = escapeHtml(text);
    // inline code (must come before emphasis so backticks don't interleave)
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    // links: [text](url) — URL is escaped already because we ran escapeHtml first
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label, url) => {
      const safeUrl = url.replace(/"/g, "&quot;");
      return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });
  }
  // bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // italic: *text* (single asterisks, not part of bold)
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  return s;
}

/** Split accumulated blockquote lines into paragraphs on blank lines. */
function quoteParagraphs(quoteBuffer: string[]): string[] {
  const paras: string[] = [];
  let cur: string[] = [];
  for (const l of quoteBuffer) {
    if (l.trim() === "") {
      if (cur.length) {
        paras.push(cur.join(" "));
        cur = [];
      }
    } else cur.push(l);
  }
  if (cur.length) paras.push(cur.join(" "));
  return paras;
}

/**
 * Pipe-separated table row → array of cell texts. Handles surrounding
 * whitespace and one optional leading/trailing pipe.
 */
function parseTableRow(line: string): string[] {
  let t = line.trim();
  if (t.startsWith("|")) t = t.slice(1);
  if (t.endsWith("|")) t = t.slice(0, -1);
  return t.split("|").map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
  const t = line.trim();
  if (!t.startsWith("|") && !t.includes("|")) return false;
  // a separator row has only -, :, |, spaces
  return /^\|?\s*:?-{2,}:?(\s*\|\s*:?-{2,}:?)+\s*\|?$/.test(t);
}

const SECTION_COMMENT_RE =
  /^<!--\s*section\s+(\d+)\s*\(id=(\d+),\s*raw_sort=(\d+)\):\s*(.*?)\s*-->$/;

type ListKind = "ul" | "ol" | null;

export function renderMarkdown(
  input: string,
  options: RenderOptions = {},
): string {
  const opts: RenderOptions = {
    headingIds: true,
    lists: true,
    arabicBlockquotes: true,
    simplifyTranslit: true,
    ...options,
  };

  // Fold scholarly Arabic transliteration to plain English for display
  // (Kīmiyāʾ al-Saʿāda → Kimiya al-Sa'ada). Arabic script is left untouched.
  const source = opts.simplifyTranslit ? simplifyTransliteration(input) : input;
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let paraBuffer: string[] = [];
  let quoteBuffer: string[] = [];
  let listKind: ListKind = null;
  let listItems: string[] = [];

  const flushPara = () => {
    if (paraBuffer.length === 0) return;
    const text = paraBuffer.join(" ").trim();
    if (text) out.push(`<p>${renderInline(text, opts)}</p>`);
    paraBuffer = [];
  };

  const flushQuote = () => {
    if (quoteBuffer.length === 0) return;
    const paras = quoteParagraphs(quoteBuffer);
    if (opts.arabicBlockquotes) {
      // Tag Arabic-script lines as `.ar` and their translations as `.tr` (only
      // when the block actually contains Arabic) so the reader can style verses
      // like the print renderer does — body-ink Arabic at body scale, no box.
      // Emission stays one line so the Composer's paragraph mirror
      // (`:scope > p`) is unaffected.
      const hasArabic = paras.some((p) => ARABIC_SCRIPT_RE.test(p));
      const inner =
        paras.length === 0
          ? "<p></p>"
          : paras
              .map((p) => {
                if (!hasArabic) return `<p>${renderInline(p, opts)}</p>`;
                return ARABIC_SCRIPT_RE.test(p)
                  ? `<p class="ar" dir="rtl" lang="ar">${renderInline(p, opts)}</p>`
                  : `<p class="tr">${renderInline(p, opts)}</p>`;
              })
              .join("");
      out.push(
        `<blockquote${hasArabic ? ' class="quran"' : ""}>${inner}</blockquote>`,
      );
    } else {
      const inner = paras
        .map((p) => {
          const t = p.trim();
          return t ? `<p>${renderInline(t, opts)}</p>` : "";
        })
        .join("");
      out.push(`<blockquote>${inner}</blockquote>`);
    }
    quoteBuffer = [];
  };

  const flushList = () => {
    if (listKind === null || listItems.length === 0) {
      listKind = null;
      listItems = [];
      return;
    }
    out.push(`<${listKind}>`);
    for (const item of listItems)
      out.push(`<li>${renderInline(item, opts)}</li>`);
    out.push(`</${listKind}>`);
    listKind = null;
    listItems = [];
  };

  const flushAll = () => {
    flushPara();
    flushQuote();
    flushList();
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].replace(/\t/g, "  ").trimEnd();
    const trimmed = line.trim();

    if (trimmed.length === 0) {
      flushAll();
      i++;
      continue;
    }

    // horizontal rule
    if (/^(---+|\*\*\*+)$/.test(trimmed)) {
      flushAll();
      out.push("<hr />");
      i++;
      continue;
    }

    // headings
    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushAll();
      const level = hMatch[1].length;
      const inner = renderInline(hMatch[2], opts);
      if (opts.headingIds) {
        // slug for in-chapter anchoring (mini-TOC). Strip HTML, lowercase, hyphenate.
        const plain = hMatch[2]
          .toLowerCase()
          .replace(/[^a-z0-9\s-]/g, "")
          .trim()
          .replace(/\s+/g, "-")
          .slice(0, 80);
        out.push(`<h${level} id="${plain}">${inner}</h${level}>`);
      } else {
        out.push(`<h${level}>${inner}</h${level}>`);
      }
      i++;
      continue;
    }

    // blockquote
    const qMatch = line.match(/^>\s?(.*)$/);
    if (qMatch) {
      flushPara();
      flushList();
      quoteBuffer.push(qMatch[1]);
      i++;
      continue;
    } else if (quoteBuffer.length > 0) {
      flushQuote();
    }

    if (opts.lists) {
      // unordered list
      const ulMatch = line.match(/^[-*+]\s+(.+)$/);
      if (ulMatch) {
        flushPara();
        flushQuote();
        if (listKind !== "ul") {
          flushList();
          listKind = "ul";
        }
        listItems.push(ulMatch[1]);
        i++;
        continue;
      }

      // ordered list
      const olMatch = line.match(/^\d+\.\s+(.+)$/);
      if (olMatch) {
        flushPara();
        flushQuote();
        if (listKind !== "ol") {
          flushList();
          listKind = "ol";
        }
        listItems.push(olMatch[1]);
        i++;
        continue;
      } else if (listKind !== null) {
        flushList();
      }
    }

    // Table: header row + separator + body (source flavor)
    if (
      opts.tables &&
      trimmed.startsWith("|") &&
      i + 1 < lines.length &&
      isTableSeparator(lines[i + 1])
    ) {
      flushAll();
      const header = parseTableRow(trimmed);
      i += 2; // skip header + separator
      const body: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        body.push(parseTableRow(lines[i]));
        i++;
      }
      const headHtml = header
        .map((c) => `<th>${renderInline(c, opts)}</th>`)
        .join("");
      const bodyHtml = body
        .map(
          (row) =>
            `<tr>${row.map((c) => `<td>${renderInline(c, opts)}</td>`).join("")}</tr>`,
        )
        .join("");
      out.push(
        `<table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`,
      );
      continue;
    }

    // HTML comments
    if (opts.sectionMarkers) {
      // Section-marker comment: `<!-- section N (id=…, raw_sort=…): label -->`
      const sm = trimmed.match(SECTION_COMMENT_RE);
      if (sm) {
        flushAll();
        const pos = sm[1];
        const id = sm[2];
        const label = sm[4];
        out.push(
          `<div class="se-section-marker" dir="ltr">` +
            `<span>§ ${pos} · id ${id}</span>` +
            (label
              ? `  <span dir="rtl" class="se-urdu-label">— ${escapeHtml(label)}</span>`
              : "") +
            `</div>`,
        );
        i++;
        continue;
      }
      if (trimmed.startsWith("<!--") && trimmed.endsWith("-->")) {
        flushAll();
        const inner = trimmed.replace(/^<!--\s*/, "").replace(/\s*-->$/, "");
        out.push(
          `<div class="se-section-marker" dir="ltr">${escapeHtml(inner)}</div>`,
        );
        i++;
        continue;
      }
    } else if (trimmed.startsWith("<!--")) {
      // Book flavor: comment line (used in transcripts: `<!-- page 1 -->`)
      flushAll();
      const inner = trimmed.replace(/^<!--\s*/, "").replace(/\s*-->$/, "");
      out.push(
        `<div class="md-comment" data-md-comment="${escapeHtml(inner)}">${escapeHtml(inner)}</div>`,
      );
      i++;
      continue;
    }

    // Image-block markers from the source-extractor finalize stage.
    if (
      opts.imageBlocks &&
      (trimmed.startsWith("[diagram") || trimmed.startsWith("[image"))
    ) {
      flushPara();
      out.push(`<p class="se-image-block">${renderInline(trimmed, opts)}</p>`);
      i++;
      continue;
    }

    // Default — accumulate prose. Source flavor accumulates the trimmed line
    // (its inputs are machine-generated, column-0 text); book flavor keeps the
    // line as-is minus trailing whitespace.
    paraBuffer.push(opts.angleMarkers ? trimmed : line);
    i++;
  }
  flushAll();

  return out.join("\n");
}

/**
 * Render a source-extractor raw-extract.md into HTML for the review view —
 * the former source-render.ts entry point, now a profile of renderMarkdown.
 * Deliberately scoped to the source-extractor view (.se-prose).
 */
export function renderSourceMarkdown(input: string): string {
  return renderMarkdown(input, SOURCE_PROFILE);
}

/**
 * Render a YAML-folded scalar as a single paragraph or as paragraphs.
 * YAML's `>` folding collapses newlines into spaces, so we typically
 * get one paragraph back. We still run renderInline so emphasis works.
 */
export function renderProse(text: string): string {
  return renderMarkdown(text);
}
