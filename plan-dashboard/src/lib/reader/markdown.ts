/**
 * Minimal markdown → HTML converter for podcast-factory prose content.
 *
 * The content uses a small subset: paragraphs, `# H1` / `## H2` / `### H3`
 * headers, `**bold**`, `*italic*`, inline `` `code` ``, and line breaks via
 * blank lines. We don't need full CommonMark, and shipping a dependency that
 * does is overkill for Phase 1.
 *
 * IMPORTANT: emphasis spans are preserved as `<em>` / `<strong>` so Phase 2's
 * highlight-renderer can wrap them in ref-category spans based on `data-ref-*`
 * attributes without re-parsing. Don't sneak class names onto these — that's
 * for Phase 2 to do.
 */

function escapeHtml(s: string): string {
  // Don't escape apostrophes — they're safe in HTML text content and inside
  // double-quoted attributes. Escaping them as &#39; breaks downstream
  // pattern matching (e.g. "Abu Ya'qub" → "Abu Ya&#39;qub" which the Arabic
  // detector can't see through). Only escape what's actually unsafe.
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderInline(text: string): string {
  let s = escapeHtml(text);
  // inline code (must come before emphasis so backticks don't interleave)
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  // links: [text](url) — URL is escaped already because we ran escapeHtml first
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label, url) => {
    const safeUrl = url.replace(/"/g, '&quot;');
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  });
  // bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // italic: *text* (single asterisks, not part of bold)
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  return s;
}

type ListKind = 'ul' | 'ol' | null;

export function renderMarkdown(input: string): string {
  const lines = input.replace(/\r\n/g, '\n').split('\n');
  const out: string[] = [];
  let paraBuffer: string[] = [];
  let quoteBuffer: string[] = [];
  let listKind: ListKind = null;
  let listItems: string[] = [];

  const flushPara = () => {
    if (paraBuffer.length === 0) return;
    const text = paraBuffer.join(' ').trim();
    if (text) out.push(`<p>${renderInline(text)}</p>`);
    paraBuffer = [];
  };

  const flushQuote = () => {
    if (quoteBuffer.length === 0) return;
    // split blockquote body into paragraphs on blank lines (already collapsed
    // since we skip empties), so join with space and emit one <p>.
    const body = quoteBuffer.map((l) => renderInline(l)).join(' ');
    out.push(`<blockquote><p>${body}</p></blockquote>`);
    quoteBuffer = [];
  };

  const flushList = () => {
    if (listKind === null || listItems.length === 0) {
      listKind = null;
      listItems = [];
      return;
    }
    out.push(`<${listKind}>`);
    for (const item of listItems) out.push(`<li>${renderInline(item)}</li>`);
    out.push(`</${listKind}>`);
    listKind = null;
    listItems = [];
  };

  const flushAll = () => { flushPara(); flushQuote(); flushList(); };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.trim().length === 0) {
      flushAll();
      continue;
    }

    // horizontal rule
    if (/^(---+|\*\*\*+)$/.test(line.trim())) {
      flushAll();
      out.push('<hr />');
      continue;
    }

    // headings
    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushAll();
      const level = hMatch[1].length;
      const inner = renderInline(hMatch[2]);
      // slug for in-chapter anchoring (mini-TOC). Strip HTML, lowercase, hyphenate.
      const plain = hMatch[2].toLowerCase().replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-').slice(0, 80);
      out.push(`<h${level} id="${plain}">${inner}</h${level}>`);
      continue;
    }

    // blockquote
    const qMatch = line.match(/^>\s?(.*)$/);
    if (qMatch) {
      flushPara();
      flushList();
      quoteBuffer.push(qMatch[1]);
      continue;
    } else if (quoteBuffer.length > 0) {
      flushQuote();
    }

    // unordered list
    const ulMatch = line.match(/^[-*+]\s+(.+)$/);
    if (ulMatch) {
      flushPara();
      flushQuote();
      if (listKind !== 'ul') { flushList(); listKind = 'ul'; }
      listItems.push(ulMatch[1]);
      continue;
    }

    // ordered list
    const olMatch = line.match(/^\d+\.\s+(.+)$/);
    if (olMatch) {
      flushPara();
      flushQuote();
      if (listKind !== 'ol') { flushList(); listKind = 'ol'; }
      listItems.push(olMatch[1]);
      continue;
    } else if (listKind !== null) {
      flushList();
    }

    // HTML comment line (used in transcripts: `<!-- page 1 -->`)
    if (line.trim().startsWith('<!--')) {
      flushAll();
      const inner = line.trim().replace(/^<!--\s*/, '').replace(/\s*-->$/, '');
      out.push(`<div class="md-comment" data-md-comment="${escapeHtml(inner)}">${escapeHtml(inner)}</div>`);
      continue;
    }

    paraBuffer.push(line);
  }
  flushAll();

  return out.join('\n');
}

/**
 * Render a YAML-folded scalar as a single paragraph or as paragraphs.
 * YAML's `>` folding collapses newlines into spaces, so we typically
 * get one paragraph back. We still run renderInline so emphasis works.
 */
export function renderProse(text: string): string {
  return renderMarkdown(text);
}
