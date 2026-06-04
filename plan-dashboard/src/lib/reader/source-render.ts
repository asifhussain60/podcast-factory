/**
 * Render a source-extractor raw-extract.md into HTML for the review view.
 *
 * The bundles use markdown plus three custom inline markers:
 *   ⟪ar:…⟫       → inline Arabic in naskh font (RTL)
 *   ⟪ar-quote:…⟫ → display-block Arabic quote
 *   ⟪quran X:Y⟫  → small editorial citation chip
 *
 * HTML comments of the shape `<!-- section N (id=…, raw_sort=…): label -->`
 * are rendered as small editorial section dividers, not stripped.
 *
 * This renderer is deliberately scoped to the source-extractor view (.se-prose).
 * It does NOT reuse the book-review markdown/highlight pipeline.
 */

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Replace ⟪…⟫ markers + emphasis. Returns HTML-safe (any literal `<`/`>` in
 * surrounding text is escaped first). Markers carry their own tags.
 */
function renderInline(text: string): string {
  // STEP 1: Slice on ⟪…⟫ markers, escape text segments, leave markers as
  // placeholders. We must escape OUTSIDE markers but not damage the marker
  // contents.
  const markerRe = /⟪([a-z-]+):([^⟪⟫]*)⟫|⟪quran (\d+):(\d+)(?:-(\d+))?⟫/g;
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = markerRe.exec(text)) !== null) {
    out += escapeHtml(text.slice(last, m.index));
    if (m[3] !== undefined) {
      // ⟪quran X:Y⟫ form
      const surah = m[3];
      const start = m[4];
      const end = m[5];
      const ref = end ? `Quran ${surah}:${start}–${end}` : `Quran ${surah}:${start}`;
      out += `<span class="quran-cite" dir="ltr">${ref}</span>`;
    } else {
      const kind = m[1]; // "ar", "ar-quote", or arbitrary "ar-*"
      const inner = m[2];
      const cls = kind === 'ar-quote' ? 'ar-quote' : 'ar';
      // Strip the trailing ZWNJ + space combos that often appear in source
      const trimmed = inner.trim();
      out += `<span class="${cls}" lang="ar" dir="rtl">${escapeHtml(trimmed)}</span>`;
    }
    last = m.index + m[0].length;
  }
  out += escapeHtml(text.slice(last));

  // STEP 2: emphasis (apply to escaped text — `*` are still raw)
  out = out.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, '$1<em>$2</em>');
  return out;
}

/**
 * Pipe-separated table row → array of cell texts. Handles surrounding whitespace
 * and one optional leading/trailing pipe.
 */
function parseTableRow(line: string): string[] {
  let t = line.trim();
  if (t.startsWith('|')) t = t.slice(1);
  if (t.endsWith('|')) t = t.slice(0, -1);
  return t.split('|').map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
  const t = line.trim();
  if (!t.startsWith('|') && !t.includes('|')) return false;
  // a separator row has only -, :, |, spaces
  return /^\|?\s*:?-{2,}:?(\s*\|\s*:?-{2,}:?)+\s*\|?$/.test(t);
}

const SECTION_COMMENT_RE = /^<!--\s*section\s+(\d+)\s*\(id=(\d+),\s*raw_sort=(\d+)\):\s*(.*?)\s*-->$/;

/**
 * The main entry point.
 */
export function renderSourceMarkdown(input: string): string {
  const lines = input.replace(/\r\n/g, '\n').split('\n');
  const out: string[] = [];
  let paraBuf: string[] = [];
  let quoteBuf: string[] = [];
  let i = 0;

  const flushPara = () => {
    if (paraBuf.length === 0) return;
    const text = paraBuf.join(' ').trim();
    if (text) out.push(`<p>${renderInline(text)}</p>`);
    paraBuf = [];
  };

  const flushQuote = () => {
    if (quoteBuf.length === 0) return;
    const inner: string[] = [];
    let para: string[] = [];
    const flushQuotePara = () => {
      if (para.length === 0) return;
      const t = para.join(' ').trim();
      if (t) inner.push(`<p>${renderInline(t)}</p>`);
      para = [];
    };
    for (const line of quoteBuf) {
      if (line.trim() === '') {
        flushQuotePara();
      } else {
        para.push(line);
      }
    }
    flushQuotePara();
    out.push(`<blockquote>${inner.join('')}</blockquote>`);
    quoteBuf = [];
  };

  while (i < lines.length) {
    const rawLine = lines[i];
    const line = rawLine.replace(/\t/g, '  ');
    const trimmed = line.trim();

    // Blank line — flush both buffers
    if (trimmed === '') {
      flushPara();
      flushQuote();
      i++;
      continue;
    }

    // Section-marker HTML comment
    const sm = trimmed.match(SECTION_COMMENT_RE);
    if (sm) {
      flushPara();
      flushQuote();
      const pos = sm[1];
      const id = sm[2];
      const label = sm[4];
      out.push(
        `<div class="se-section-marker" dir="ltr">` +
          `<span>§ ${pos} · id ${id}</span>` +
          (label
            ? `  <span dir="rtl" class="se-urdu-label">— ${escapeHtml(label)}</span>`
            : '') +
          `</div>`,
      );
      i++;
      continue;
    }

    // Other HTML comments — render small dimmed marker (rare)
    if (trimmed.startsWith('<!--') && trimmed.endsWith('-->')) {
      flushPara();
      flushQuote();
      const inner = trimmed.replace(/^<!--\s*/, '').replace(/\s*-->$/, '');
      out.push(`<div class="se-section-marker" dir="ltr">${escapeHtml(inner)}</div>`);
      i++;
      continue;
    }

    // Headings
    const hm = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (hm) {
      flushPara();
      flushQuote();
      const level = hm[1].length;
      out.push(`<h${level}>${renderInline(hm[2])}</h${level}>`);
      i++;
      continue;
    }

    // Horizontal rule
    if (/^-{3,}$/.test(trimmed) || /^\*{3,}$/.test(trimmed)) {
      flushPara();
      flushQuote();
      out.push('<hr />');
      i++;
      continue;
    }

    // Blockquote line
    if (trimmed.startsWith('>')) {
      flushPara();
      quoteBuf.push(trimmed.replace(/^>\s?/, ''));
      i++;
      continue;
    } else {
      // Non-quote line breaks any open blockquote
      flushQuote();
    }

    // Table: header row + separator + body
    if (trimmed.startsWith('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      flushPara();
      const header = parseTableRow(trimmed);
      i += 2; // skip header + separator
      const body: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        body.push(parseTableRow(lines[i]));
        i++;
      }
      const headHtml = header.map((c) => `<th>${renderInline(c)}</th>`).join('');
      const bodyHtml = body
        .map((row) => `<tr>${row.map((c) => `<td>${renderInline(c)}</td>`).join('')}</tr>`)
        .join('');
      out.push(`<table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`);
      continue;
    }

    // Image-block markers from the source-extractor finalize stage:
    //   [diagram: alt-text]
    //     (see ../images/NNN.png)
    //     *Arabic labels in image:* ⟪ar:…⟫
    //     *Note:* …
    // For simplicity we treat each line as its own paragraph.
    if (trimmed.startsWith('[diagram') || trimmed.startsWith('[image')) {
      flushPara();
      out.push(`<p class="se-image-block">${renderInline(trimmed)}</p>`);
      i++;
      continue;
    }

    // Default — accumulate prose
    paraBuf.push(trimmed);
    i++;
  }
  flushPara();
  flushQuote();

  return out.join('\n');
}
