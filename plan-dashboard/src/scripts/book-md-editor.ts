/**
 * book-md-editor.ts — the chapter prose editor for the Book Composer (v2).
 *
 * The SAME TipTap engine the Studio "podcast editor" (StudioEditor) uses — here as a
 * focused, framework-free surface (`@tiptap/core` + StarterKit) bound to ONE
 * chapter of the reading edition (book.md). It mounts on the chapter body, seeds
 * from that chapter's rendered HTML, and serializes the ProseMirror doc back to
 * the book.md markdown subset (headings, paragraphs, blockquotes, lists, rules,
 * bold/italic/code/strike/links) — the same serializer conventions StudioEditor uses.
 * Persistence is the caller's job (PUT /api/studio/book-md).
 */
import { Editor, Extension } from "@tiptap/core";
import type { Extensions } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import type { Node as PMNode } from "@tiptap/pm/model";

/** The only class names the editor is allowed to carry through from the seed
 *  HTML. `quran` marks an Arabic-bearing quotation block, `ar` its Arabic line,
 *  `tr` the English rendering — the three markdown.ts emits (markdown.ts:188-207)
 *  and the three every quotation stylesheet keys off. */
const PRESERVED_CLASSES = new Set(["quran", "ar", "tr"]);

/**
 * QuotationClasses — re-admit the verse markup TipTap would otherwise discard.
 *
 * StarterKit's paragraph and blockquote nodes have no `class` attribute, so
 * ProseMirror drops it on parse. The consequence was visible: a verse that reads
 * as centred maroon Arabic over its rendering in Read mode collapsed into an
 * ordinary italic grey blockquote the moment you switched to Edit, and the only
 * way to check verse formatting was to leave the editor.
 *
 * Only the three known class names survive, and only those — an attacker-supplied
 * or hand-pasted class cannot ride in. Nothing here can reach book.md:
 * docToMarkdown (below) dispatches on `node.type.name` and reads exactly one
 * attribute, `heading.level`. Attributes are presentation-only by construction.
 */
const QuotationClasses = Extension.create({
  name: "quotationClasses",
  addGlobalAttributes() {
    return [
      {
        types: ["paragraph", "blockquote"],
        attributes: {
          class: {
            default: null,
            parseHTML: (element) => {
              const kept = (element.getAttribute("class") ?? "")
                .split(/\s+/)
                .filter((c) => PRESERVED_CLASSES.has(c));
              return kept.length ? kept.join(" ") : null;
            },
            renderHTML: (attrs) =>
              attrs.class ? { class: String(attrs.class) } : {},
          },
        },
      },
    ];
  },
});

export interface ChapterEditor {
  editor: Editor;
  toMarkdown: () => string;
  destroy: () => void;
}

/** Walk a block node's inline content, preserving mark syntax. Mirrors
 *  StudioEditor.serializeInline, extended with code / strike / link. */
function serializeInline(node: PMNode): string {
  let out = "";
  node.forEach((child) => {
    if (!child.isText || !child.text) {
      out += serializeInline(child);
      return;
    }
    let text = child.text;
    const marks = child.marks.map((m) => m.type.name);
    if (marks.includes("code")) text = `\`${text}\``;
    if (marks.includes("strike")) text = `~~${text}~~`;
    const bold = marks.includes("bold");
    const italic = marks.includes("italic");
    if (bold && italic) text = `***${text}***`;
    else if (bold) text = `**${text}**`;
    else if (italic) text = `*${text}*`;
    const link = child.marks.find((m) => m.type.name === "link");
    if (link?.attrs?.href) text = `[${text}](${link.attrs.href})`;
    out += text;
  });
  return out;
}

/** Serialize the whole doc to the book.md markdown subset. */
function docToMarkdown(editor: Editor): string {
  const lines: string[] = [];
  editor.state.doc.forEach((node) => {
    const type = node.type.name;
    if (type === "heading") {
      lines.push(
        "#".repeat(Number(node.attrs.level) || 2) + " " + serializeInline(node),
      );
    } else if (type === "blockquote") {
      // A blank `>` between paragraphs keeps the reader's flushQuote splitting an
      // Arabic line from its translation (otherwise they merge into one run).
      const q: string[] = [];
      node.forEach((child, _off, i) => {
        if (i > 0) q.push("");
        const t = serializeInline(child).trimEnd();
        if (t) q.push(...t.split("\n"));
      });
      if (!q.length) lines.push(">");
      else q.forEach((l) => lines.push(l === "" ? ">" : `> ${l}`));
    } else if (type === "bulletList" || type === "orderedList") {
      let n = 1;
      node.forEach((li) => {
        const t = serializeInline(li).trim();
        lines.push(type === "orderedList" ? `${n++}. ${t}` : `- ${t}`);
      });
    } else if (type === "codeBlock") {
      lines.push("```", node.textContent, "```");
    } else if (type === "horizontalRule") {
      lines.push("---");
    } else {
      lines.push(serializeInline(node));
    }
    lines.push("");
  });
  return lines.join("\n").trimEnd() + "\n";
}

/**
 * The drag type carrying a visual's id from the Artifacts palette to the page.
 *
 * Deliberately NOT `text/plain`: a contenteditable treats a plain-text drop as
 * something to insert, so the id landed in the prose as a paragraph. A custom
 * type is invisible to that path — nothing but our own handlers can read it.
 */
export const VISUAL_DRAG_TYPE = "application/x-cx-visual";

/** Mount a chapter editor into `el`, seeded from `html`. `extraExtensions`
 *  appends to the base [StarterKit] set — e.g. the shared StudioDecos
 *  decoration plugin (verse chips, section badges, Arabic overlay), so the
 *  Composer can gain the same live-editing decorations Edit & Enrich has. */
export function mountChapterEditor(
  el: HTMLElement,
  html: string,
  extraExtensions: Extensions = [],
): ChapterEditor {
  const editor = new Editor({
    element: el,
    extensions: [StarterKit, QuotationClasses, ...extraExtensions],
    content: html,
    editorProps: {
      attributes: { class: "cx-prose", "aria-label": "Chapter prose editor" },
      // A visual dragged from the Artifacts palette is a LAYOUT action, never
      // content: swallow it here so ProseMirror cannot insert the drag payload
      // as prose. Returning true marks the drop handled and leaves the document
      // untouched; the composer's own listener does the placement. Without this
      // the editor accepted the drop as text and wrote bare `slide-4` /
      // `slide-15` paragraphs straight into book.md (found 2026-07-21).
      handleDrop: (_view, event) =>
        Array.from((event as DragEvent).dataTransfer?.types ?? []).includes(
          VISUAL_DRAG_TYPE,
        ),
    },
  });
  return {
    editor,
    toMarkdown: () => docToMarkdown(editor),
    destroy: () => editor.destroy(),
  };
}
