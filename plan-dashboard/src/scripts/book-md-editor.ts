/**
 * book-md-editor.ts — the chapter prose editor for the Book Composer (v2).
 *
 * The SAME TipTap engine the Studio "podcast editor" (StudioPoc) uses — here as a
 * focused, framework-free surface (`@tiptap/core` + StarterKit) bound to ONE
 * chapter of the reading edition (book.md). It mounts on the chapter body, seeds
 * from that chapter's rendered HTML, and serializes the ProseMirror doc back to
 * the book.md markdown subset (headings, paragraphs, blockquotes, lists, rules,
 * bold/italic/code/strike/links) — the same serializer conventions StudioPoc uses.
 * Persistence is the caller's job (PUT /api/studio/book-md).
 */
import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import type { Node as PMNode } from "@tiptap/pm/model";

export interface ChapterEditor {
  editor: Editor;
  toMarkdown: () => string;
  destroy: () => void;
}

/** Walk a block node's inline content, preserving mark syntax. Mirrors
 *  StudioPoc.serializeInline, extended with code / strike / link. */
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

/** Mount a chapter editor into `el`, seeded from `html`. */
export function mountChapterEditor(
  el: HTMLElement,
  html: string,
): ChapterEditor {
  const editor = new Editor({
    element: el,
    extensions: [StarterKit],
    content: html,
    editorProps: {
      attributes: { class: "cx-prose", "aria-label": "Chapter prose editor" },
    },
  });
  return {
    editor,
    toMarkdown: () => docToMarkdown(editor),
    destroy: () => editor.destroy(),
  };
}
