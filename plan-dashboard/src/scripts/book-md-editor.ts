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
import { Editor, Extension, Node } from "@tiptap/core";
import type { Extensions } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Heading from "@tiptap/extension-heading";
import type { Node as PMNode } from "@tiptap/pm/model";
import { originalBookSrc } from "../lib/reader/book-images";

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
  // Which CARD a quotation is drawn in (2026-08-09). Asif photographed a Qur'anic
  // verse in Edit set in the plain maroon this repo used before the cards, while
  // Read and the PDF drew it in gold on its own plate — the same chapter, the same
  // book, two answers. The class was being emitted and dropped HERE, which is the
  // one place that can strip it.
  //
  // The card's HEADER is a separate question and stays out of Edit deliberately:
  // `renderEditSeed` passes `quoteBands: false` because the band is a span INSIDE
  // the blockquote, and `docToMarkdown` writes a blockquote from its CONTENT — so
  // a band in the editor could be saved into book.md as text. A class cannot: it
  // dispatches on `node.type.name` and reads exactly one attribute.
  "k-quran",
  "k-hadith",
  "k-poem",
  "k-quote",
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
          "data-q-label": {
            default: null,
            parseHTML: (element) => {
              const raw = element.getAttribute("data-q-label") ?? "";
              return raw.trim() ? raw.trim() : null;
            },
            renderHTML: (attrs) =>
              attrs["data-q-label"]
                ? { "data-q-label": String(attrs["data-q-label"]) }
                : {},
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

/**
 * ChapterImage — the fix for a real bug, not a feature.
 *
 * StarterKit carries no image node, and nothing here ever added one. The seed
 * HTML `renderEditSeed` produces for a content image is already correct —
 * `<figure class="md-figure"><img src="…" alt="…" loading="lazy" /></figure>`,
 * from markdown.ts's own image branch — but with no NodeSpec to match it,
 * ProseMirror's DOM parser drops the whole thing on mount: an `<img>` has no
 * children, so the default "descend into children" behavior for an unknown
 * tag leaves nothing behind. Found 2026-08-14 by checking a real chapter's
 * live editor DOM (`document.querySelector('.ProseMirror').innerHTML`) and
 * seeing `<img` was simply absent, on a chapter whose book.md carries three
 * image lines. Since docToMarkdown only serializes what is IN the document,
 * the next autosave after any edit to that chapter would have silently
 * deleted all three — this is very likely the same class of bug that
 * `figure-decos.ts`'s own docstring already names as having happened once
 * before, for a different image system: "bare slide-8/slide-6/slide-3
 * paragraphs... surviving a round-trip through a schema with no image node."
 *
 * A real NodeSpec, not a decoration, is the correct fix HERE — unlike the
 * AI-visuals palette figures `figure-decos.ts` deliberately keeps out of the
 * document, an inline image's position IS the prose: the author placed it at
 * that exact point in book.md, so it belongs in the document the same way a
 * paragraph does. `atom: true` (no editable content) and `draggable: true`
 * are the standard shape for an image node; `docToMarkdown` below MUST always
 * emit `![](src)` back, verified byte-identical by a round-trip test, or this
 * fix would just move the corruption from "vanishes" to "arrives mangled."
 *
 * `alt` defaults to "" and is rendered back ONLY when non-empty — every real
 * book.md image line checked has no alt text, and `renderMarkdown`'s own
 * comment says why: "inventing one would be describing a picture this code
 * cannot see." Emitting `alt=""` unconditionally would rewrite book.md bytes
 * on the next unrelated autosave of any chapter holding an image.
 */
/** What the resize handle and align buttons persist to, on drag-release / click.
 *  A no-op default keeps `editorExtensions()` callable with no config (every
 *  existing test, and the round-trip suite this node was added for) — only
 *  the live mount in book-composer.ts supplies a real one, since only it has
 *  a slug and a selected chapter to save against. */
export interface ChapterImageDeps {
  onResize?: (
    src: string,
    layout: { height_px?: number; align?: string },
  ) => void;
}

const ALIGN_IDS = ["left", "center", "right"] as const;
/** Mirrors image-layout.mjs's own DEFAULT_HEIGHT_PX/MIN/MAX — duplicated,
 *  not imported, because that module reaches `node:fs` and this one runs in
 *  the browser. See image-layout.mjs's header for why height replaced width
 *  as the unit on 2026-08-14. */
const DEFAULT_HEIGHT_PX = 350;
const MIN_HEIGHT_PX = 60;
const MAX_HEIGHT_PX = 1200;

const ChapterImage = Node.create<ChapterImageDeps>({
  name: "chapterImage",
  group: "block",
  atom: true,
  draggable: true,
  addOptions() {
    return { onResize: undefined };
  },
  addAttributes() {
    return {
      src: { default: null },
      alt: { default: "" },
      // Both null by default — an image nobody has resized carries no
      // attribute at all, matching image-layout.mjs's own "default is
      // absence" contract, so a book with no sidecar renders identically
      // whether or not this attribute machinery exists.
      // Neither attribute defines its own parseHTML/renderHTML — the
      // node-level `getAttrs` (parse) and `renderHTML` (render) below own
      // both directions entirely, because the value has to move to a
      // DIFFERENT element than the one TipTap would default to (the figure)
      // — height as `--img-h` on the <img>, matching every other renderer's
      // convention, align as `data-align` on the <figure>. Height, not width,
      // as of 2026-08-14 — image-layout.mjs's header has the full reasoning.
      heightPx: { default: null },
      align: { default: null },
      // The book.md-relative path (`images/79/…jpg`), recovered from `src`
      // (`/api/studio/book-image?...`) — NOT rendered onto the DOM, only
      // carried in the node's own attrs. `src` has to be the browser-facing
      // route for the <img> to load at all (see composer.ts's own
      // `serveBookImages` note); `docToMarkdown` and the resize-persistence
      // call below both need the ORIGINAL path instead, because that is the
      // key `image-layout.json` is keyed by and the address book.md itself
      // stores. Recomputed on every parse via `originalBookSrc`, so it can
      // never drift from `src` the way a second stored copy could.
      origSrc: { default: null },
    };
  },
  parseHTML() {
    return [
      {
        tag: "figure.md-figure",
        // A rule-level getAttrs takes full control of the parsed attrs — the
        // per-attribute `parseHTML` functions above are NEVER consulted once
        // this runs, so heightPx/align have to be read here too, not just
        // declared on the attrs (found while verifying resize survives a
        // reload: it silently reset every time until this was added).
        getAttrs: (dom) => {
          const el = dom as HTMLElement;
          const img = el.querySelector("img");
          const src = img?.getAttribute("src");
          if (!img || !src) return false;
          // `--img-h` lives on the <img>'s own inline style — the same
          // custom-property convention every renderer uses (see the note on
          // the image branch in markdown.ts).
          const hProp = (img as HTMLImageElement).style.getPropertyValue(
            "--img-h",
          );
          const h = Number(hProp.replace("px", ""));
          const a = el.dataset.align;
          return {
            src,
            origSrc: originalBookSrc(src),
            alt: img.getAttribute("alt") ?? "",
            heightPx:
              Number.isInteger(h) && h >= MIN_HEIGHT_PX && h <= MAX_HEIGHT_PX
                ? h
                : null,
            align: a && (ALIGN_IDS as readonly string[]).includes(a) ? a : null,
          };
        },
      },
    ];
  },
  renderHTML({ node }) {
    const { src, alt, heightPx, align } = node.attrs as {
      src: string;
      alt: string;
      heightPx: number | null;
      align: string | null;
    };
    const figureAttrs: Record<string, string> = { class: "md-figure" };
    if (align) figureAttrs["data-align"] = align;
    const imgAttrs: Record<string, string> = { src, alt, loading: "lazy" };
    if (heightPx) imgAttrs.style = `--img-h:${heightPx}px`;
    return ["figure", figureAttrs, ["img", imgAttrs]];
  },
  // A NodeView so the image can carry a live resize handle and align toolbar
  // in the edit canvas — this is presentation ON TOP of the node, never a
  // second place book.md's shape is decided. Dragging updates the node's own
  // attrs (so undo/redo and the live width both work through ProseMirror's
  // normal transaction flow) and, on release, calls `onResize` to persist —
  // the same "attrs are the source of truth in the doc, the callback is what
  // reaches disk" split every other stateful decoration in this file uses.
  addNodeView() {
    return ({ node, getPos, editor }) => {
      const wrap = document.createElement("figure");
      wrap.className = "md-figure cx-image-figure";
      wrap.contentEditable = "false";

      const img = document.createElement("img");
      img.loading = "lazy";
      wrap.appendChild(img);

      const handle = document.createElement("div");
      handle.className = "cx-image-resize-handle";
      handle.setAttribute("role", "slider");
      handle.setAttribute("aria-label", "Resize image");
      handle.setAttribute("tabindex", "0");
      wrap.appendChild(handle);

      const toolbar = document.createElement("div");
      toolbar.className = "cx-image-align-toolbar";
      const buttons = ALIGN_IDS.map((id) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "cx-image-align-btn";
        b.dataset.align = id;
        b.title = `Align ${id}`;
        b.textContent = id === "left" ? "⇤" : id === "right" ? "⇥" : "⇔";
        b.addEventListener("click", () => {
          const pos = getPos();
          if (typeof pos !== "number") return;
          editor
            .chain()
            .setNodeSelection(pos)
            .updateAttributes("chapterImage", { align: id })
            .run();
          // origSrc, not src: image-layout.json is keyed by the book.md path
          // (see the attribute's own docstring above), never the API route.
          const origSrc = String(node.attrs.origSrc ?? node.attrs.src ?? "");
          if (origSrc) this.options.onResize?.(origSrc, { align: id });
        });
        toolbar.appendChild(b);
        return b;
      });
      wrap.appendChild(toolbar);

      // `--img-h` rather than a direct `style.height` write: the visual value
      // is per-instance data, exactly like `visual-layout.mjs`'s own
      // `--fig-w` custom property for the OTHER image system — the actual
      // height RULE stays in the external stylesheet (`height: var(--img-h,
      // 350px)`), this only ever supplies the number.
      const applyAttrs = (attrs: typeof node.attrs) => {
        img.src = String(attrs.src ?? "");
        img.alt = String(attrs.alt ?? "");
        if (attrs.heightPx)
          img.style.setProperty("--img-h", `${attrs.heightPx}px`);
        else img.style.removeProperty("--img-h");
        wrap.dataset.align = attrs.align || "center";
        buttons.forEach((b) => {
          b.classList.toggle(
            "is-active",
            b.dataset.align === (attrs.align || "center"),
          );
        });
      };
      applyAttrs(node.attrs);

      // Vertical drag only (height: not diagonal — see the handle's own
      // `cursor: ns-resize` in book-composer.css): width is never dragged
      // directly, it falls out of the browser's own aspect-ratio math once
      // height is set.
      let dragStartY = 0;
      let dragStartPx = DEFAULT_HEIGHT_PX;
      const onPointerMove = (e: PointerEvent) => {
        const deltaPx = e.clientY - dragStartY;
        const next = Math.max(
          MIN_HEIGHT_PX,
          Math.min(MAX_HEIGHT_PX, Math.round(dragStartPx + deltaPx)),
        );
        img.style.setProperty("--img-h", `${next}px`);
        handle.dataset.px = String(next);
      };
      const onPointerUp = () => {
        document.removeEventListener("pointermove", onPointerMove);
        document.removeEventListener("pointerup", onPointerUp);
        const pos = getPos();
        const px = Number(handle.dataset.px);
        if (typeof pos !== "number" || !Number.isInteger(px)) return;
        editor
          .chain()
          .setNodeSelection(pos)
          .updateAttributes("chapterImage", {
            heightPx: px === DEFAULT_HEIGHT_PX ? null : px,
          })
          .run();
        const origSrc = String(node.attrs.origSrc ?? node.attrs.src ?? "");
        if (origSrc) this.options.onResize?.(origSrc, { height_px: px });
      };
      handle.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        dragStartY = e.clientY;
        dragStartPx = Number(node.attrs.heightPx) || DEFAULT_HEIGHT_PX;
        document.addEventListener("pointermove", onPointerMove);
        document.addEventListener("pointerup", onPointerUp);
      });

      return {
        dom: wrap,
        update: (updated) => {
          if (updated.type.name !== "chapterImage") return false;
          applyAttrs(updated.attrs);
          return true;
        },
      };
    };
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
    } else if (type === "chapterImage") {
      const alt = String(node.attrs.alt ?? "").trim();
      // origSrc, never src: `src` is the browser-facing API route (see the
      // attribute's own docstring) — book.md must keep the portable
      // book-relative path the PDF build resolves against. Falls back to
      // `src` only for a node built by hand (e.g. a test) with no origSrc.
      const src = String(node.attrs.origSrc ?? node.attrs.src ?? "");
      lines.push(`![${alt}](${src})`);
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
 * - `heading` (disabled on StarterKit, replaced below) — a chapter body only
 *   ever authors levels 3-5 (`##` is reserved for the book's chapter
 *   boundaries; see book-composer.ts's `headingLevels` remap), but the NODE
 *   itself still parses and renders all six — narrowing `levels` was tried
 *   and reverted (2026-08-14): it changes what a bare `##`/`#` line PARSES
 *   AS, not merely which shortcut sets it, and fence-decos.test.ts pins the
 *   case that a `## ` line matching a pipeline marker's text is a HEADING,
 *   undecorated, precisely because it parses as one. What actually needed
 *   narrowing was the KEYBOARD SHORTCUT: Tiptap's Heading extension binds
 *   `Mod-Alt-{level}` for every configured level, so with all six live,
 *   `Mod-Alt-1`/`Mod-Alt-2` insert a real level-1/2 heading into chapter
 *   prose — a fake book title or chapter boundary, one stray keystroke away.
 *   `HeadingShortcutsOnly` below is the levels-untouched, schema-preserving
 *   fix: the same node, with its own `addKeyboardShortcuts()` replaced
 *   entirely rather than merged, so only three keys get a binding at all —
 *   `Mod-Alt-1/2/3`, matching the TOOLBAR's numbering (Heading 1/2/3) rather
 *   than the markdown level each actually sets (3/4/5), by Asif's request
 *   (2026-08-14) once the default `Mod-Alt-{level}` numbering read as
 *   off-by-two against what the dropdown shows. `Mod-Alt-4`/`Mod-Alt-5`/
 *   `Mod-Alt-6` are therefore unbound, same as `Mod-Alt-1`/`Mod-Alt-2` were
 *   before this remap — nothing here re-opens the corruption risk above,
 *   since the KEY strings changed but the `level` each still sets did not.
 */
const HeadingShortcutsOnly = Heading.extend({
  addKeyboardShortcuts() {
    return {
      "Mod-Alt-1": () => this.editor.commands.toggleHeading({ level: 3 }),
      "Mod-Alt-2": () => this.editor.commands.toggleHeading({ level: 4 }),
      "Mod-Alt-3": () => this.editor.commands.toggleHeading({ level: 5 }),
    };
  },
});

/** "Body" (plain paragraph), beside the heading shortcuts above rather than a
 *  node's own — StarterKit's Paragraph has no keyboard shortcut to override.
 *  `Mod-Alt-0` matches the "0 = normal text" convention the 1/2/3 set above
 *  already carries, and is unclaimed by anything else in this schema. */
const ParagraphShortcut = Extension.create({
  name: "paragraphShortcut",
  addKeyboardShortcuts() {
    return { "Mod-Alt-0": () => this.editor.commands.setParagraph() };
  },
});

export function editorExtensions(
  extra: Extensions = [],
  chapterImageDeps: ChapterImageDeps = {},
): Extensions {
  return [
    StarterKit.configure({
      underline: false,
      hardBreak: false,
      link: { autolink: false, linkOnPaste: false, openOnClick: false },
      heading: false,
    }),
    HeadingShortcutsOnly,
    ParagraphShortcut,
    QuotationClasses,
    ListItemValue,
    ChapterImage.configure(chapterImageDeps),
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
  chapterImageDeps: ChapterImageDeps = {},
): ChapterEditor {
  const editor = new Editor({
    element: el,
    extensions: editorExtensions(extraExtensions, chapterImageDeps),
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
