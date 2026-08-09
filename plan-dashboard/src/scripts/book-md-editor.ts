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
 *  and the three every quotation stylesheet keys off.
 *
 *  `aside` and its three kinds joined them on 2026-08-05. markdown.ts tags a
 *  pipeline-authored span `blockquote.aside.editorial` (or `.bridge` /
 *  `.study-summary`) so a stylesheet can draw it as a panel rather than as the
 *  book's own words; dropped here, Edit mode showed the note as a plain
 *  blockquote between two grey marker strips, which is what Asif saw. Same
 *  guarantee as the other three: docToMarkdown dispatches on `node.type.name`
 *  and reads exactly one attribute (`heading.level`), so a class carried here is
 *  presentation and can never reach book.md. */
export const PRESERVED_CLASSES = new Set([
  "quran",
  "ar",
  "tr",
  // Scripture, resolved against the canonical mushaf. Joined the list on
  // 2026-08-09, with `renderEditSeed` finally being handed the provenance set:
  // dropped here the class could not survive the parse even once it was emitted,
  // so the edit canvas would still have shown a verse and a hadith as the same
  // thing. Same guarantee as the three above — docToMarkdown names no class, so
  // this is presentation and cannot reach book.md.
  "is-quranic",
  "aside",
  "editorial",
  "bridge",
  "study-summary",
]);

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

/**
 * ListItemValue — carry an ordered item's SOURCE ordinal through the round trip.
 *
 * `renderMarkdown` deliberately puts the stated number on each `<li value="N">`
 * rather than trusting `<ol>`'s own counter, because this corpus contains a list
 * that legitimately starts at 3 and an author style that repeats "1." per item
 * (markdown.ts flushList). StarterKit's listItem has no `value` attribute, so
 * ProseMirror dropped it on parse and docToMarkdown renumbered every list from 1
 * — silently rewriting the one real enumeration in the corpus on the first
 * autosave. That is the faked numbering REQ-015 forbids, written into book.md.
 *
 * An item with no stated ordinal (anything the toolbar creates) keeps `null` and
 * falls back to counting, so a new list numbers 1, 2, 3 as expected.
 */
const ListItemValue = Extension.create({
  name: "listItemValue",
  addGlobalAttributes() {
    return [
      {
        types: ["listItem"],
        attributes: {
          value: {
            default: null,
            parseHTML: (element) => {
              const raw = element.getAttribute("value");
              if (raw === null) return null;
              const n = Number(raw);
              return Number.isInteger(n) ? n : null;
            },
            renderHTML: (attrs) =>
              typeof attrs.value === "number"
                ? { value: String(attrs.value) }
                : {},
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

/** Serialize a ProseMirror doc to the book.md markdown subset. Takes the doc
 *  node (not the Editor) so the round-trip test can drive the same serializer
 *  the live editor saves through, without mounting a view. */
export function docToMarkdown(doc: PMNode): string {
  const lines: string[] = [];
  doc.forEach((node) => {
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
      // The ordinal an item STATES wins over the position it happens to hold —
      // see ListItemValue. Only an item with no stated ordinal counts up.
      let n = Number(node.attrs.start) || 1;
      node.forEach((li) => {
        const t = serializeInline(li).trim();
        if (type !== "orderedList") {
          lines.push(`- ${t}`);
          return;
        }
        const stated = typeof li.attrs.value === "number" ? li.attrs.value : n;
        lines.push(`${stated}. ${t}`);
        n = stated + 1;
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

/**
 * The editor's extension set — one definition, shared by the live mount and the
 * round-trip test, so the schema the test parses with can never drift from the
 * schema the Composer actually edits in.
 *
 * The StarterKit overrides all answer the same question: can a keystroke produce
 * something docToMarkdown would drop, or something book.md's renderers cannot
 * read back? If yes, the capability leaves the schema — a mark the toolbar can
 * no longer reach is still reachable by its shortcut, so hiding a button is not
 * a fix.
 *
 * - `underline` — book.md has no underline syntax. serializeInline never emitted
 *   it, so Mod-U silently discarded on save.
 * - `hardBreak` — serializeInline emits nothing for a childless leaf, so
 *   Shift+Enter fused the words either side of it ("one<br>two" -> "onetwo").
 *   Neither renderMarkdown nor the print renderer emits or parses `<br>`, so
 *   there is no representation to save it AS; the honest fix is to not offer it.
 * - `link.autolink` / `linkOnPaste` — on by default, so typing a bare domain in
 *   prose wrote `[text](href)` into book.md and the PDF gained a link nobody
 *   authored. Links are now deliberate only.
 * - `link.openOnClick` — a click inside the editor navigated the browser away,
 *   discarding whatever the autosave debounce had not yet flushed.
 */
export function editorExtensions(extra: Extensions = []): Extensions {
  return [
    StarterKit.configure({
      underline: false,
      hardBreak: false,
      link: { autolink: false, linkOnPaste: false, openOnClick: false },
    }),
    QuotationClasses,
    ListItemValue,
    ...extra,
  ];
}

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
    extensions: editorExtensions(extraExtensions),
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
    toMarkdown: () => docToMarkdown(editor.state.doc),
    destroy: () => editor.destroy(),
  };
}
