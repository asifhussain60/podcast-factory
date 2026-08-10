/**
 * A small, self-contained markdown renderer for Claude Code's plan files.
 *
 * Deliberately NOT `src/lib/reader/markdown.ts`: that renderer (693 lines) is
 * built for book prose — Arabic-aware blockquotes, pipeline machine-fence
 * markers, Quranic-run tagging — and has no fenced code-block support, only
 * inline `code`. A plan file is written for Claude to execute against, so it
 * routinely has fenced snippets with file paths; forcing it through the book
 * renderer would either misrender those or drag irrelevant machinery into an
 * unrelated page. This covers exactly what a plan needs: headings, bold/
 * italic, inline code, fenced code blocks, lists, links, paragraphs.
 *
 * The masked view (Asif, 2026-08-08): a plan is written for an engineer, full
 * of file paths and code. Asif reads it as a non-technical reader, so each
 * block is classified `prose` or `technical`; the masked render shows prose
 * inline and tucks each section's technical blocks under one collapsed
 * disclosure — nothing deleted, just layered, "a masked view on top of that."
 */

type BlockType = "heading" | "code" | "list" | "para" | "blockquote";

interface Block {
  type: BlockType;
  level?: number; // heading level
  html: string;
  technical: boolean;
}

const TECHNICAL_HEADING_RE =
  /\b(files?|implementation|verification|schema|new files|route|nav wiring|gating)\b/i;
const CODE_SPAN_RE = /`[^`]+`/g;
const PATH_TOKEN_RE = /\b[\w.-]+\/[\w./-]+\b/g;

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Bold/italic/inline-code/links — the inline subset a plan actually uses. */
function renderInline(text: string): string {
  let s = escapeHtml(text);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");
  s = s.replace(
    /\[([^\]]+)\]\(([^)\s]+)\)/g,
    '<a href="$2" rel="noopener">$1</a>',
  );
  return s;
}

/** How much of a text block reads as engineering detail rather than prose. */
function technicalDensity(rawLines: string[]): boolean {
  const text = rawLines.join(" ");
  const codeSpans = text.match(CODE_SPAN_RE)?.length ?? 0;
  const pathTokens = text.match(PATH_TOKEN_RE)?.length ?? 0;
  const words = text.split(/\s+/).filter(Boolean).length || 1;
  return (codeSpans + pathTokens) / words > 0.12 || codeSpans + pathTokens >= 4;
}

function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.length === 0) {
      i++;
      continue;
    }

    // Fenced code block — always technical.
    const fence = trimmed.match(/^```(\S*)$/);
    if (fence) {
      const lang = fence[1] || "";
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && lines[i].trim() !== "```") {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      blocks.push({
        type: "code",
        technical: true,
        html: `<pre class="cp-code"><code${lang ? ` class="lang-${escapeHtml(lang)}"` : ""}>${escapeHtml(codeLines.join("\n"))}</code></pre>`,
      });
      continue;
    }

    // Heading.
    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const headingText = heading[2].trim();
      blocks.push({
        type: "heading",
        level,
        technical: TECHNICAL_HEADING_RE.test(headingText),
        html: `<h${level + 1}>${renderInline(headingText)}</h${level + 1}>`,
      });
      i++;
      continue;
    }

    // Blockquote.
    if (/^>\s?/.test(trimmed)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i++;
      }
      blocks.push({
        type: "blockquote",
        technical: technicalDensity(quoteLines),
        html: `<blockquote>${quoteLines.map((l) => `<p>${renderInline(l)}</p>`).join("")}</blockquote>`,
      });
      continue;
    }

    // List (ul or ol), including blank-line-separated loose items.
    const ulItem = trimmed.match(/^[-*+]\s+(.+)$/);
    const olItem = trimmed.match(/^\d+\.\s+(.+)$/);
    if (ulItem || olItem) {
      const kind: "ul" | "ol" = ulItem ? "ul" : "ol";
      const itemLines: string[] = [];
      const itemRe = kind === "ul" ? /^[-*+]\s+(.+)$/ : /^\d+\.\s+(.+)$/;
      while (i < lines.length) {
        const t = lines[i].trim();
        if (t.length === 0) {
          // a single blank line continues a loose list only if the next
          // non-blank line is still an item of the same kind.
          let j = i + 1;
          while (j < lines.length && lines[j].trim().length === 0) j++;
          if (j < lines.length && itemRe.test(lines[j].trim())) {
            i = j;
            continue;
          }
          break;
        }
        const m = t.match(itemRe);
        if (!m) break;
        itemLines.push(m[1]);
        i++;
      }
      blocks.push({
        type: "list",
        technical: technicalDensity(itemLines),
        html: `<${kind}>${itemLines.map((l) => `<li>${renderInline(l)}</li>`).join("")}</${kind}>`,
      });
      continue;
    }

    // Paragraph — everything up to the next blank line or structural marker.
    const paraLines: string[] = [];
    while (i < lines.length && lines[i].trim().length > 0) {
      const t = lines[i].trim();
      if (
        /^```/.test(t) ||
        /^#{1,4}\s/.test(t) ||
        /^>\s?/.test(t) ||
        /^[-*+]\s+/.test(t) ||
        /^\d+\.\s+/.test(t)
      ) {
        break;
      }
      paraLines.push(t);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({
        type: "para",
        technical: technicalDensity(paraLines),
        html: `<p>${renderInline(paraLines.join(" "))}</p>`,
      });
    } else {
      i++; // structural line that matched nothing above — avoid an infinite loop
    }
  }

  return blocks;
}

/** Every block rendered in order — the raw technical read. */
export function renderFull(text: string): string {
  return parseBlocks(text)
    .map((b) => b.html)
    .join("\n");
}

/** Prose inline; each section's technical blocks collapsed under one
 *  disclosure, closed by default, placed where that section ends. */
export function renderMasked(text: string): string {
  const blocks = parseBlocks(text);
  const out: string[] = [];
  let techBuffer: Block[] = [];

  const flush = () => {
    if (techBuffer.length === 0) return;
    out.push(
      `<details class="cp-technical"><summary>Technical detail</summary>${techBuffer
        .map((b) => b.html)
        .join("\n")}</details>`,
    );
    techBuffer = [];
  };

  for (const block of blocks) {
    if (block.type === "heading") {
      flush();
      out.push(block.html);
      continue;
    }
    if (block.technical) {
      techBuffer.push(block);
      continue;
    }
    out.push(block.html);
  }
  flush();

  return out.join("\n");
}
