/**
 * The Book Composer's toolbar: which controls exist, their icons, their tooltips,
 * and what the markdown serializer is required to cover.
 *
 * Split out of book-composer.ts on 2026-08-16, when that file passed its size
 * ratchet. Configuration rather than logic, which is what makes it the right
 * thing to move first: nothing here reads the DOM or closes over composer state,
 * so it can be read — and changed — without holding the 4,000-line boot sequence
 * in mind.
 */

export const WRAP_MAX = 50;

// anchorKey comes from the single shared implementation — see the import above.

/**
 * Everything `docToMarkdown` actually knows how to write.
 *
 * Declared by hand rather than derived from the schema on purpose: deriving it
 * would make the package's coverage assertion agree with itself and check
 * nothing. Adding a node to editorExtensions without also teaching the
 * serializer about it must fail loudly here, not quietly in book.md.
 */
export const DOC_TO_MARKDOWN_COVERS = [
  "doc",
  "text",
  "paragraph",
  "heading",
  "blockquote",
  "bulletList",
  "orderedList",
  "listItem",
  "codeBlock",
  "horizontalRule",
  "chapterImage",
  "bold",
  "italic",
  "code",
  "strike",
  "link",
];

/**
 * The text-colour button's two hooks into the page.
 *
 * Module scope because COMPOSE_TOOLBAR_ITEMS is built once, at load, while the
 * chapter the button acts on changes underneath it on every chapter switch.
 * `boot()` assigns both; until it does, the button is inert rather than wrong.
 */

export const COMPOSE_TOOLBAR_TIPS = {
  undo: { title: "Undo", detail: "Step back through your last edits. ⌘Z." },
  redo: { title: "Redo", detail: "Reapply an edit you undid. ⇧⌘Z." },
  paragraphFormat: {
    title: "Paragraph style",
    detail: "Body or Heading 1–3. ⌥⌘1/2/3 for Heading 1/2/3, ⌥⌘0 for Body.",
  },
  bold: { title: "Bold", detail: "Select text and click. ⌘B." },
  italic: {
    title: "Italic",
    detail:
      "Select text and click. Used for book titles and emphasis. ⌘I. Arabic never slants — it is left upright.",
  },
  bulletList: {
    title: "Bulleted list",
    detail: "Turns the selected paragraphs into a list. Click again to undo.",
  },
  orderedList: {
    title: "Numbered list",
    detail:
      "Turns the selected paragraphs into a numbered list. A list that starts at a number the source states keeps that number.",
  },
  blockquote: {
    title: "Quotation",
    detail:
      "Sets the selected paragraphs as an indented quotation — for a passage quoted from elsewhere. An Arabic line above its English rendering prints as the book's verse style; the two are told apart by what they contain, so no separate control is needed.",
  },
  quoteKind: {
    title: "Quote kind",
    detail:
      "Select a quotation, then declare what it is — a Saying, a Verse, or a Prophetic tradition. The reading edition draws a different card for each. Qur'an is never declared here — it is recognized automatically.",
  },
  link: {
    title: "Link",
    detail: "Select the words to link, click, then type the address.",
  },
  horizontalRule: {
    title: "Divider",
    detail:
      "Inserts a horizontal rule at the cursor — a break between two passages inside one chapter, not a new chapter.",
  },
};
