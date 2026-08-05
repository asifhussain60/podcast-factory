/**
 * fence-decos.ts — show the pipeline's machine fence markers AS markers in the
 * live edit canvas, instead of as a stray line of prose.
 *
 * The problem. `book.md` carries comment markers that delimit spans the Python
 * phases own — `<!-- edition-intro:begin -->`, `editorial:`, `bridge:`,
 * `study-summary:` (see FENCE_KINDS in lib/reader/book-fences.ts). The reader
 * renderer turns a comment line into a `.md-comment` div, TipTap's StarterKit
 * schema has no HTML-comment node, so the div collapses to an ordinary
 * paragraph and the marker arrives in the editor as BARE TEXT. On a book whose
 * front matter opens the first chapter, that made `edition-intro:begin` the
 * visible first line of the chapter, indistinguishable from the author's prose.
 *
 * Why decorate rather than remove. That bare text is load-bearing: it is exactly
 * what `preserveFences` step 1 reads to restore the comment form after a save,
 * and step 1 is the lossless path. Dropping the marker from the editor seed
 * would demote `edition-intro` — the fence whose loss once stacked a second
 * introduction on every compose — onto the heuristic re-wrap path. So the text
 * stays in the document and only its PRESENTATION changes.
 *
 * Decorations live outside the document (the same reason figure-decos.ts uses
 * them), so nothing here can reach `toMarkdown()` and nothing here can alter
 * what a save writes.
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

import { FENCE_KINDS } from "../../../lib/reader/book-fences";

/** A marker as it survives into the editor: the comment delimiters are gone, so
 *  the paragraph's whole text is `kind:begin` / `kind:end`. Built from the
 *  contract's own kind list, so a new fence kind is covered automatically. */
const FENCE_TEXT_RE = new RegExp(
  `^(?:${FENCE_KINDS.join("|")}):(?:begin|end)$`,
);

/** True when a paragraph's text is nothing but a machine fence marker. */
export function isFenceMarkerText(text: string): boolean {
  return FENCE_TEXT_RE.test(text.trim());
}

/**
 * Positions of every top-level paragraph that is only a fence marker.
 *
 * Split out as a pure function so the contract is testable without mounting an
 * editor view — the decoration below is a thin wrapper over it.
 */
export function fenceMarkerRanges(doc: PmNode): { from: number; to: number }[] {
  const ranges: { from: number; to: number }[] = [];
  doc.forEach((node, offset) => {
    if (node.type.name !== "paragraph") return;
    if (!isFenceMarkerText(node.textContent)) return;
    ranges.push({ from: offset, to: offset + node.nodeSize });
  });
  return ranges;
}

const key = new PluginKey("cxFenceDecos");

/** Style fence-marker paragraphs as machine markers. Presentation only. */
export function createFenceDecos(): Extension {
  return Extension.create({
    name: "cxFenceDecos",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key,
          props: {
            decorations(state) {
              const decos = fenceMarkerRanges(state.doc).map((r) =>
                Decoration.node(r.from, r.to, {
                  class: "cx-fence-marker",
                  // Announced and hoverable: the line looks inert, so say what
                  // it is and that removing it is not a formatting choice.
                  title:
                    "Pipeline marker — leave this line in place; it tells the " +
                    "pipeline where this section begins and ends.",
                }),
              );
              return DecorationSet.create(state.doc, decos);
            },
          },
        }),
      ];
    },
  });
}
