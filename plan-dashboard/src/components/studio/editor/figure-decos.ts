/**
 * figure-decos.ts — renders the Book Composer's PLACED figures inside the live
 * TipTap edit canvas.
 *
 * Why decorations and not nodes. A figure's home is `book/visual-layout.json`,
 * never the prose: `book.md` carries the author's words and nothing else, and
 * the layout file carries where each visual sits. Modelling a figure as a real
 * editor node would put it in the document, and anything in the document is
 * serialized by `toMarkdown()` on the next autosave — which is exactly how bare
 * `slide-8` / `slide-6` / `slide-3` paragraphs (an <img>'s alt text, surviving a
 * round-trip through a schema with no image node) once landed in book.md.
 * Widget decorations live outside the document by construction, so that class of
 * corruption cannot recur no matter what the user does in the editor.
 *
 * Positioning mirrors the PDF renderer's `applyLayout` and the composer's own
 * `insertFiguresInline`: idx<=0 => chapter top; idx=N => after the Nth top-level
 * paragraph; idx beyond the paragraph count => flushed at the end. Figures
 * sharing an index keep their placement order.
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

import type { Box } from "./studio-decos";

/** One placed figure, ready to draw. `key` must change whenever `el` would
 *  render differently, so an unchanged figure keeps its DOM across transactions
 *  (and, with it, a loaded <img> that would otherwise flicker on every keypress). */
export interface EditorFigure {
  /** Paragraph index this figure follows — the placement's `anchor_para`. */
  idx: number;
  /** Identity for decoration reuse; include every visual property that matters. */
  key: string;
  /** Builds the figure element. Called only when the key changes. */
  el: () => HTMLElement;
}

export interface FigureDecosBag {
  /** Figures for the chapter currently open in the editor. Mutated by the
   *  composer; it dispatches an empty transaction to request a redraw. */
  figuresRef: Box<EditorFigure[]>;
}

export function createFigureDecos(bag: FigureDecosBag) {
  const { figuresRef } = bag;

  return Extension.create({
    name: "composerFigures",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey("composerFigures"),
          props: {
            decorations(state) {
              const figures = figuresRef.current;
              if (!figures.length) return DecorationSet.empty;

              // Top-level paragraph boundaries, in document order. `applyLayout`
              // counts only paragraphs — not headings or blockquotes — so the
              // editor must count the same set or a figure drifts between the
              // canvas and the printed page.
              const paraEnds: number[] = [];
              let docEnd = 0;
              state.doc.forEach((node: PmNode, offset: number) => {
                docEnd = offset + node.nodeSize;
                if (node.type.name === "paragraph")
                  paraEnds.push(offset + node.nodeSize);
              });

              const decos: Decoration[] = [];
              for (const fig of figures) {
                const pos =
                  fig.idx <= 0
                    ? 0
                    : fig.idx > paraEnds.length
                      ? docEnd
                      : paraEnds[fig.idx - 1];
                decos.push(
                  Decoration.widget(pos, () => fig.el(), {
                    // side>0 keeps the figure after the paragraph it follows;
                    // the key makes an unchanged figure reuse its DOM node.
                    side: 1,
                    key: fig.key,
                  }),
                );
              }
              return DecorationSet.create(state.doc, decos);
            },
          },
        }),
      ];
    },
  });
}
