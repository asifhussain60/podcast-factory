/**
 * compose-quran-command.ts — the Composer's own toolbar button, registered
 * through the editor package's extension point.
 *
 * This lives HERE, not in the package: the package knows nothing about verses,
 * scripture or this book format, and a test in it fails if that vocabulary ever
 * appears there. What it provides is the registration surface; what a host
 * provides is the meaning.
 *
 * The structure below is the ONE shape that survives the round trip, and every
 * part of it is load-bearing:
 *
 *   blockquote.quran
 *     ├─ p.ar   the Arabic run
 *     └─ p.tr   the rendering
 *
 * `quran`, `ar` and `tr` are the only classes QuotationClasses re-admits on
 * parse (book-md-editor.ts PRESERVED_CLASSES), so anything else set here is
 * silently dropped on the next reload and the button would appear to forget.
 * `dir` and `lang` are deliberately absent — direction is CSS on this surface.
 *
 * docToMarkdown ignores the classes entirely and writes the blockquote with a
 * blank `>` between its paragraphs; renderEditSeed then RE-DERIVES `quran`/`ar`/
 * `tr` from the content on the way back in. That is what makes this safe: the
 * classes describe what the text is, so they are never carried in the markdown
 * and can never disagree with it.
 *
 * Consequence worth knowing: type Arabic into the translation line and the
 * classes flip on reload. That is correct — they describe content — and the
 * button deliberately does not fight it. It is a one-shot insert, not a node
 * type that maintains itself.
 */
import { TextSelection } from "@tiptap/pm/state";
import { defineButton } from "@asifhussain/prose-editor";
import type { RegisteredButton } from "@asifhussain/prose-editor";

/** An inline SVG, matching the package's 16px stroke grid. */
const VERSE_ICON =
  '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" ' +
  'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
  'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
  '<path d="M2.5 3.5h11"/><path d="M4 7h8"/><path d="M2.5 10.5h11"/>' +
  '<path d="M6 13.5h4"/></svg>';

export function quranQuotationButton(): RegisteredButton {
  return defineButton({
    id: "quranQuotation",
    label: "Quranic quotation",
    tooltip: "Insert a Quranic quotation (Arabic over its rendering)",
    icon: { svg: VERSE_ICON },
    priority: 44,
    isActive: (state) => state.isActive("blockquote", { class: "quran" }),
    run: (api) => {
      // If the selection already sits in one, toggling out is the useful
      // action — otherwise the button can only ever nest quotes.
      if (api.state.isActive("blockquote", { class: "quran" })) {
        void api.chain().focus().toggleBlockquote().run();
        return;
      }
      // Seed the Arabic line with whatever was selected, so marking an
      // existing verse is one click rather than retyping it.
      const selected = api.getSelectedText().trim();
      const insertedAt = api.editor.state.selection.from;
      void api
        .chain()
        .focus()
        .insertContent({
          type: "blockquote",
          attrs: { class: "quran" },
          content: [
            {
              type: "paragraph",
              attrs: { class: "ar" },
              ...(selected
                ? { content: [{ type: "text", text: selected }] }
                : {}),
            },
            { type: "paragraph", attrs: { class: "tr" } },
          ],
        })
        // insertContent leaves the caret AFTER the inserted block — which for a
        // scaffold means the button drops you outside the thing it just made,
        // and the toolbar reports the quotation as inactive because the caret is
        // not in it. Put the caret in the Arabic line, which is what the user is
        // about to type into.
        .command(({ tr, dispatch }) => {
          if (!dispatch) return true;
          let target: number | null = null;
          tr.doc.descendants((node, pos) => {
            if (
              target === null &&
              pos >= insertedAt - 1 &&
              node.type.name === "blockquote" &&
              node.attrs.class === "quran"
            ) {
              target = pos;
            }
            return target === null;
          });
          if (target === null) return true;
          // +2: past the blockquote's own boundary, then into its first child.
          dispatch(
            tr.setSelection(TextSelection.near(tr.doc.resolve(target + 2))),
          );
          return true;
        })
        .run();
    },
  });
}
