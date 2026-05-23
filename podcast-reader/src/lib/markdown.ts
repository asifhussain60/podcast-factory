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
  // bold: **text**
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // italic: *text* (single asterisks, not part of bold)
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  return s;
}

export function renderMarkdown(input: string): string {
  const lines = input.replace(/\r\n/g, '\n').split('\n');
  const out: string[] = [];
  let paraBuffer: string[] = [];

  const flushPara = () => {
    if (paraBuffer.length === 0) return;
    const text = paraBuffer.join(' ').trim();
    if (text) out.push(`<p>${renderInline(text)}</p>`);
    paraBuffer = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.trim().length === 0) {
      flushPara();
      continue;
    }

    // headings
    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushPara();
      const level = hMatch[1].length;
      out.push(`<h${level}>${renderInline(hMatch[2])}</h${level}>`);
      continue;
    }

    // HTML comment line (used in transcripts: `<!-- page 1 -->`)
    if (line.trim().startsWith('<!--')) {
      flushPara();
      // render as small dimmed marker
      const inner = line.trim().replace(/^<!--\s*/, '').replace(/\s*-->$/, '');
      out.push(`<div class="md-comment" data-md-comment="${escapeHtml(inner)}">${escapeHtml(inner)}</div>`);
      continue;
    }

    paraBuffer.push(line);
  }
  flushPara();

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
