/**
 * book-html.mjs — the SINGLE HTML-assembly source for a book's reading edition.
 *
 * Extracted from render-book-pdf.mjs (studio-composer REQ-SC-022) so the printed
 * PDF and the in-browser Preview (Studio redesign Phase 3) consume identical
 * markup instead of two hand-synced renderers. Pure — no Playwright, no
 * process.argv, no filesystem writes; every function here only reads book
 * content and returns strings.
 *
 * Callers:
 *   - scripts/render-book-pdf.mjs — wraps buildBookHtml() output in a full
 *     <html> document + print CSS, serves it locally, and screenshots it to
 *     PDF via Playwright.
 *   - src/pages/studio/[slug]/preview.astro — calls buildBookHtml() directly
 *     at SSR time (same Node runtime, no subprocess) and paginates the result
 *     client-side with vendored Paged.js.
 */
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { loadLayout, applyLayout } from "../visual-layout.mjs";

const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const ARABIC_INLINE_RE = /[﴿«]?[\s؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+[﴾»]?/g;
const NUMBER_WORDS = [
  "",
  "One",
  "Two",
  "Three",
  "Four",
  "Five",
  "Six",
  "Seven",
  "Eight",
  "Nine",
  "Ten",
  "Eleven",
  "Twelve",
  "Thirteen",
  "Fourteen",
  "Fifteen",
  "Sixteen",
  "Seventeen",
  "Eighteen",
  "Nineteen",
  "Twenty",
  "Twenty-One",
  "Twenty-Two",
  "Twenty-Three",
  "Twenty-Four",
  "Twenty-Five",
  "Twenty-Six",
  "Twenty-Seven",
  "Twenty-Eight",
  "Twenty-Nine",
  "Thirty",
];

export function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
export function renderInline(text) {
  let s = escapeHtml(text);
  s = s.replace(ARABIC_INLINE_RE, (match) => {
    if (!ARABIC_RE.test(match)) return match;
    const leading = match.match(/^\s*/)?.[0] || "";
    const trailing = match.match(/\s*$/)?.[0] || "";
    const body = match.slice(leading.length, match.length - trailing.length);
    return `${leading}<span class="ar-inline" dir="rtl" lang="ar">${body}</span>${trailing}`;
  });
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  return s;
}

export function extractToc(md) {
  const items = [];
  const headingRe = /^##\s+(.+)$/gm;
  let match;
  let sawNumbered = false;
  while ((match = headingRe.exec(md)) !== null) {
    const raw = match[1].trim();
    const numbered = raw.match(/^(\d+)\.\s+(.+)$/);
    if (numbered) {
      sawNumbered = true;
      items.push({ label: numbered[1], title: numbered[2].trim() });
    } else if (!sawNumbered && items.length === 0) {
      items.push({ label: items.length === 0 ? "Preface" : "", title: raw });
    }
  }
  return items;
}

export function renderToc(items) {
  if (!items.length) return "";
  const rows = items
    .map((item) => {
      const label = item.label
        ? `<span class="toc-label">${escapeHtml(item.label)}</span>`
        : "";
      return `<li>${label}<span class="toc-title">${renderInline(item.title)}</span></li>`;
    })
    .join("");
  return `<section class="toc-page"><p class="toc-eyebrow">Contents</p><h2>Contents</h2><ol>${rows}</ol></section>`;
}
/** ASCII-fold a display name (meta.yml authors carry diacritics). */
export function asciiFold(s) {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[ʻʿ‘’ʼ]/g, "'");
}
/** Read the author display name from the book's meta.yml (best effort). */
export function readAuthor(bookContentDir) {
  const metaPath = path.join(bookContentDir, "meta.yml");
  if (!existsSync(metaPath)) return "";
  const line = readFileSync(metaPath, "utf-8")
    .split(/\r?\n/)
    .find((l) => /^\s*author:\s*/.test(l));
  if (!line) return "";
  let value = line.replace(/^\s*author:\s*/, "").trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return asciiFold(value.trim());
}
/** Read the per-book citation-style family from book/citation-style.json.
 *  Returns 'plain' | 'scholarly' | 'elegant', or '' when the file is absent or
 *  the value is unknown (renderer then leaves the body unstyled = default look). */
export function readCitationFamily(bookDir) {
  const p = path.join(bookDir, "citation-style.json");
  if (!existsSync(p)) return "";
  try {
    const family = JSON.parse(readFileSync(p, "utf-8"))?.family;
    return ["plain", "scholarly", "elegant"].includes(family) ? family : "";
  } catch {
    return "";
  }
}
/** Map visual_id -> { src, embeddedTitle } from book/visuals/index.json (v2).
 *  Absent index (today's state) yields an empty map — the layout applier then
 *  no-ops, so rendering is unchanged. */
export function readVisualAssets(bookContentDir) {
  const p = path.join(bookContentDir, "book", "visuals", "index.json");
  const map = new Map();
  if (!existsSync(p)) return map;
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    for (const v of data?.visuals || []) {
      if (!v?.id || !v?.file) continue;
      map.set(String(v.id), {
        src: `/book/visuals/${v.file}`,
        embeddedTitle: String(v.embedded_title || ""),
      });
    }
  } catch {
    /* tolerant: a bad index just means no contract-driven figures */
  }
  return map;
}

export function readCrosswalk(bookContentDir) {
  const p = path.join(bookContentDir, "book", "source-crosswalk.json");
  if (!existsSync(p)) return [];
  try {
    const data = JSON.parse(readFileSync(p, "utf-8"));
    return Array.isArray(data?.chapters) ? data.chapters : [];
  } catch {
    return [];
  }
}

export function renderSourceCrosswalk(items) {
  if (!items.length) return "";
  const rows = items
    .map((item) => {
      const n = item.index ? String(item.index) : "";
      const range =
        item.arabic_source_page_range || item.source_page_range || "";
      const heads =
        Array.isArray(item.source_headings) && item.source_headings.length
          ? item.source_headings.slice(0, 3).join("; ")
          : (item.source_excerpt || "").slice(0, 140);
      return (
        `<tr><td>${escapeHtml(n)}</td><td>${renderInline(item.title || "")}</td>` +
        `<td>${escapeHtml(range)}</td><td>${renderInline(heads || "")}</td></tr>`
      );
    })
    .join("");
  return (
    '<section class="crosswalk-page"><p class="toc-eyebrow">Source Crosswalk</p>' +
    "<h2>Source Crosswalk</h2>" +
    "<table><thead><tr><th>Ch.</th><th>Chapter</th><th>Arabic pages</th><th>Source signal</th></tr></thead>" +
    `<tbody>${rows}</tbody></table></section>`
  );
}

/** Minimal renderer matching markdown.ts behaviour for book.md (headings,
 *  paragraphs, blockquotes, and raw HTML blocks like <figure class="book-diagram">). */
export function renderMd(md, crosswalkByIndex = new Map(), opts = {}) {
  // selfStudy (opt-in): the render-time self-study layer. When false (default)
  // every branch below is skipped, so the reading-edition render is byte-for-byte
  // unchanged. When true it additionally parses markdown bullet lists into <ul>
  // and turns the source-grounded editorial fences (produced by 0book-augment,
  // <!-- editorial:begin -->…<!-- editorial:end -->) into distinctly-styled
  // Contextual-Note / Study-summary asides instead of plain blockquotes.
  const selfStudy = opts.selfStudy === true;
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let para = [];
  let quote = [];
  let list = [];
  let inHtmlBlock = false;
  let chapterJustOpened = false;
  let sawH2 = false;
  // Self-study editorial-aside capture state.
  let aside = null; // { kind: 'note' | 'summary', body: string[] }

  const ASIDE_META = {
    note: { cls: "study-note", label: "Contextual note" },
    summary: { cls: "study-summary", label: "Study summary" },
  };
  const flushList = () => {
    if (!list.length) return;
    out.push(
      `<ul class="study-list">${list.map((li) => `<li>${renderInline(li)}</li>`).join("")}</ul>`,
    );
    list = [];
  };
  const flushAside = () => {
    if (!aside) return;
    const meta = ASIDE_META[aside.kind];
    const paras = [];
    let cur = [];
    for (const l of aside.body) {
      if (l.trim() === "") {
        if (cur.length) {
          paras.push(cur.join(" "));
          cur = [];
        }
      } else cur.push(l);
    }
    if (cur.length) paras.push(cur.join(" "));
    const inner =
      paras.map((p) => `<p>${renderInline(p)}</p>`).join("") || "<p></p>";
    out.push(
      `<aside class="${meta.cls}"><p class="study-aside-label">${meta.label}</p>${inner}</aside>`,
    );
    aside = null;
  };

  const flushPara = () => {
    if (!para.length) return;
    const cls = chapterJustOpened ? ' class="ch-first"' : "";
    chapterJustOpened = false;
    out.push(`<p${cls}>${renderInline(para.join(" "))}</p>`);
    para = [];
  };
  const flushQuote = () => {
    if (!quote.length) return;
    const paras = [];
    let cur = [];
    for (const l of quote) {
      if (l.trim() === "") {
        if (cur.length) {
          paras.push(cur.join(" "));
          cur = [];
        }
      } else cur.push(l);
    }
    if (cur.length) paras.push(cur.join(" "));
    const hasArabic = paras.some((p) => ARABIC_RE.test(p));
    if (hasArabic) {
      // Mushaf treatment: Arabic lines RTL + Amiri, translations centered below.
      const inner = [];
      paras.forEach((p, i) => {
        if (ARABIC_RE.test(p)) {
          // Strip a stray trailing ASCII period — Latin punctuation has no
          // place at the end of an Arabic line (bidi renders it mid-air).
          const cleaned = p.trim().replace(/\.\s*$/, "");
          inner.push(
            `<p class="ar" dir="rtl" lang="ar">${renderInline(cleaned)}</p>`,
          );
          if (i < paras.length - 1) inner.push('<hr class="quran-divider">');
        } else {
          inner.push(`<p class="tr">${renderInline(p)}</p>`);
        }
      });
      out.push(`<blockquote class="quran">${inner.join("")}</blockquote>`);
    } else {
      out.push(
        `<blockquote>${paras.map((p) => `<p>${renderInline(p)}</p>`).join("") || "<p></p>"}</blockquote>`,
      );
    }
    quote = [];
  };

  for (const line of lines) {
    // Raw HTML block pass-through: <figure class="book-diagram">...</figure>
    if (inHtmlBlock) {
      out.push(line);
      if (line.trimEnd().toLowerCase() === "</figure>") inHtmlBlock = false;
      continue;
    }
    // Self-study: capture the source-grounded editorial fences (0book-augment)
    // and study-summary fences into distinctly-styled asides. Outside self-study
    // these fall through untouched (comment lines are invisible; the > lines
    // render as an ordinary blockquote — the reading edition is unchanged).
    if (selfStudy) {
      if (aside) {
        if (/<!--\s*(?:editorial|study-summary):end\s*-->/.test(line)) {
          flushAside();
          continue;
        }
        const body = line.replace(/^>\s?/, "");
        if (!/^\*\*.+\*\*\s*$/.test(body.trim())) aside.body.push(body); // drop the bold label line
        continue;
      }
      const beginSummary = /<!--\s*study-summary:begin\s*-->/.test(line);
      const beginNote = /<!--\s*editorial:begin\s*-->/.test(line);
      if (beginSummary || beginNote) {
        flushPara();
        flushQuote();
        flushList();
        aside = { kind: beginSummary ? "summary" : "note", body: [] };
        continue;
      }
    }
    // The editorial/study-summary/bridge fences are machine markers, never
    // visible text. Self-study consumes editorial/study-summary into styled
    // asides (above); every other case (default reading edition, and bridge
    // fences always) skips the marker line so it never renders as escaped
    // <!-- --> text — the fenced content's own lines render as ordinary prose.
    if (
      /^<!--\s*(?:editorial|study-summary|bridge):(?:begin|end)\s*-->$/.test(
        line.trim(),
      )
    ) {
      continue;
    }
    if (line.trimStart().toLowerCase().startsWith("<figure")) {
      flushPara();
      flushQuote();
      flushList();
      out.push(line);
      inHtmlBlock = !line.includes("</figure>");
      continue;
    }
    const h = line.match(/^(#{1,6})\s+(.+)$/);
    if (h) {
      flushPara();
      flushQuote();
      flushList();
      const level = h[1].length;
      const text = h[2].trim();
      if (level === 2) {
        // Book-style chapter opening. "N. Title" → CHAPTER N eyebrow + bare
        // title; the unnumbered first h2 is the preface. Later unnumbered H2s
        // are internal source headings and must stay in the prose flow.
        const isFirstH2 = !sawH2;
        const numbered = text.match(/^(\d+)\.\s+(.+)$/);
        let eyebrow;
        let title;
        if (numbered) {
          const n = parseInt(numbered[1], 10);
          eyebrow = `Chapter ${NUMBER_WORDS[n] || numbered[1]}`;
          title = numbered[2];
        } else {
          eyebrow = sawH2 ? "" : "Preface";
          title = text;
        }
        if (numbered || isFirstH2) {
          const sourceRange = numbered
            ? crosswalkByIndex.get(parseInt(numbered[1], 10))
                ?.arabic_source_page_range ||
              crosswalkByIndex.get(parseInt(numbered[1], 10))
                ?.source_page_range ||
              ""
            : "";
          sawH2 = true;
          chapterJustOpened = true;
          out.push(
            `<section class="chapter-open${isFirstH2 ? " first-chapter-open" : ""}">` +
              (eyebrow
                ? `<p class="ch-eyebrow">${escapeHtml(eyebrow)}</p>`
                : "") +
              `<h2>${renderInline(title)}</h2>` +
              (sourceRange
                ? `<p class="ch-source">Arabic source ${escapeHtml(sourceRange)}</p>`
                : "") +
              '<hr class="ch-rule">' +
              "</section>",
          );
        } else {
          out.push(`<h3 class="section-heading">${renderInline(text)}</h3>`);
        }
      } else {
        out.push(`<h${level}>${renderInline(text)}</h${level}>`);
      }
      continue;
    }
    // Self-study: markdown bullet lists → <ul> (default render has no list
    // parser, so a '- ' line stays inline in a paragraph — unchanged when off).
    if (selfStudy) {
      const li = line.match(/^\s*[-*]\s+(.+)$/);
      if (li) {
        flushPara();
        flushQuote();
        list.push(li[1]);
        continue;
      }
      if (list.length) flushList();
    }
    const q = line.match(/^>\s?(.*)$/);
    if (q) {
      flushPara();
      flushList();
      quote.push(q[1]);
      continue;
    }
    if (quote.length) flushQuote();
    if (line.trim() === "") {
      flushPara();
      flushList();
      continue;
    }
    para.push(line);
  }
  flushPara();
  flushQuote();
  flushList();
  flushAside();
  return out.join("\n");
}

export function themeRoot(css) {
  const m = css.match(/:root\s*\{([^}]*)\}/);
  return m ? m[1] : "";
}

/**
 * buildBookHtml(mdPath, { v2 }) — the single HTML-assembly entry point.
 *
 * Reads book.md (at mdPath) plus its sibling contract files (meta.yml,
 * citation-style.json, source-crosswalk.json, and — when v2 is true —
 * visual-layout.json + visuals/index.json) and returns every markup fragment
 * a caller needs to build a full document: cover, title page, TOC, source
 * crosswalk, and the chapter body (with v2 figure placement already applied).
 * Callers own their own document shell (doctype/head/print-CSS for the PDF
 * path, the Astro page shell + Paged.js for Preview) — this function only
 * ever returns body-level HTML fragments, never a full <html> document.
 */
export function buildBookHtml(mdPath, { v2 = false, selfStudy = false } = {}) {
  const md = readFileSync(mdPath, "utf-8");
  const titleMatch = md.match(/^#\s+(.+)$/m);
  const title = titleMatch
    ? titleMatch[1].trim()
    : path.basename(mdPath, ".md");
  const body = md.replace(/^#\s+.+$\n?/m, "");
  const tocItems = extractToc(body);

  // Static-asset root: the book's content dir (parent of book/), so markdown
  // can reference e.g. <img src="slide-deck/_pages/page-02.png">.
  const assetRoot = path.resolve(path.dirname(mdPath), "..");
  const author = readAuthor(assetRoot);
  const crosswalk = readCrosswalk(assetRoot);
  const crosswalkByIndex = new Map(
    crosswalk.map((item) => [Number(item.index), item]),
  );
  const coverPath = path.join(path.dirname(mdPath), "cover.png");
  const hasCover = existsSync(coverPath);

  const coverHtml = hasCover
    ? `<section class="cover"><img src="/book/cover.png" alt="">` +
      `<div class="cover-panel"><h1>${escapeHtml(title)}</h1>` +
      (author ? `<p class="cover-author">${escapeHtml(author)}</p>` : "") +
      `</div></section>`
    : "";
  const titlePage =
    `<section class="title-page"><p class="eyebrow">Reading edition</p>` +
    `<h1>${escapeHtml(title)}</h1>` +
    (author ? `<p class="title-author">${escapeHtml(author)}</p>` : "") +
    `<hr class="title-rule">` +
    `<div class="disclaimer-panel">Generated using podcast-factory AI. Verify content; AI can make mistakes.</div>` +
    `</section>`;

  // v2: honor the human-curated visual-layout.json contract. Figures are placed
  // ONLY from the contract (book.md stays diagram-free). Absent/partial contract
  // is tolerated — applyLayout no-ops when there are no placements or assets.
  let bodyHtml = renderMd(body, crosswalkByIndex, { selfStudy });
  const bodyClasses = [];
  if (selfStudy) bodyClasses.push("book-self-study");
  if (v2) {
    bodyClasses.push("book-v2");
    const { placements, warnings } = loadLayout(assetRoot);
    if (warnings.length)
      warnings.forEach((w) => console.error(`  [visual-layout] ${w}`));
    if (placements.length) {
      bodyHtml = applyLayout(bodyHtml, placements, readVisualAssets(assetRoot));
    }
  }
  // Citation & quote family (book/citation-style.json) — global per-book choice
  // made in /studio/<slug>/style. Applies regardless of the v2 flag; absent file
  // or unknown value falls back to the unstyled default (scholarly look). Adds a
  // body.style-<family> hook that book-print.css reskins passage blocks with.
  const family = readCitationFamily(path.dirname(mdPath));
  if (family) bodyClasses.push(`style-${family}`);
  const bodyClass = bodyClasses.join(" ");

  return {
    title,
    author,
    assetRoot,
    coverHtml,
    titlePage,
    tocHtml: renderToc(tocItems),
    crosswalkHtml: renderSourceCrosswalk(crosswalk),
    bodyHtml,
    bodyClass,
  };
}
