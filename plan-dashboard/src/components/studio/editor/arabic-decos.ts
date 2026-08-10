/**
 * arabic-decos.ts — paint the reader's inline-Arabic treatment onto the live
 * edit canvas.
 *
 * The seed HTML already wraps every inline Arabic run in `<span class="ar-inline">`
 * (isolateInlineArabic, markdown.ts) — that is what gives Read mode the term's
 * larger size (--q-ar-inline-size) and its own face (--q-ar-face). But TipTap's
 * schema has no node or mark for a bare `<span>`, and `QuotationClasses`
 * (book-md-editor.ts) only preserves `class` on `paragraph`/`blockquote` — so
 * the wrapper is discarded on parse and the run reaches the live doc as
 * unstyled text: the browser's fallback serif, at parity with the Latin body,
 * which a vowelled Arabic word reads as fine print against (quote-typography.css
 * explains why --q-ar-inline-size exists at all). `.cx-prose .ar-raw` in
 * book-composer.css has stood ready for exactly this since the Composer's
 * Arabic-quotation rules were written; this is the decoration that paints it.
 *
 * A DECORATION, never a mark — for the same reason colour-decos.ts is one. A
 * schema mark would be something docToMarkdown could be asked to serialize, and
 * book.md has no syntax to serialize it INTO. A decoration cannot reach the
 * document at all: it is recomputed from the doc's own text on every render.
 *
 * Matches `findArabicRuns`, exported from markdown.ts, so "what counts as an
 * inline Arabic run" cannot drift between the read-mode wrapper and this one.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

import { findArabicRuns } from "../../../lib/reader/markdown";

function build(doc: PmNode): DecorationSet {
  const decos: Decoration[] = [];
  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return true;
    for (const r of findArabicRuns(node.text)) {
      decos.push(
        Decoration.inline(pos + r.start, pos + r.end, {
          class: "ar-raw",
          dir: "rtl",
          lang: "ar",
        }),
      );
    }
    return false;
  });
  return DecorationSet.create(doc, decos);
}

export function createArabicDecos(): Extension {
  return Extension.create({
    name: "arabicRawDecos",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey("arabicRawDecos"),
          props: {
            decorations(state) {
              return build(state.doc);
            },
          },
        }),
      ];
    },
  });
}
