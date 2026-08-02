/**
 * colour-decos.ts — paint a chapter's stored text colours in the edit canvas.
 *
 * A DECORATION, never a mark, and that is the load-bearing choice. A schema mark
 * would be something `docToMarkdown` could be asked to serialize, and book.md has
 * no syntax to serialize it INTO — so the colour would be silently dropped on the
 * next autosave, which is the failure this repo has already been bitten by twice
 * (underline, hard breaks). A decoration cannot reach the document at all: it is
 * drawn from the sidecar, and the sidecar is the only thing a save writes.
 *
 * Directly modelled on companion-decos.ts, which tints annotated passages the
 * same way and for the same reason. Both use the shared passage matcher, so a
 * quote is found here exactly as it is found in Read mode and in the PDF.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

import {
  flatten,
  findPassage,
  type PassageChunk,
} from "../../../lib/reader/companion/passage-match";

/** One coloured run, as the sidecar stores it. */
export interface ColourSpan {
  quote: string;
  ink: string;
}

export interface ColourDecosOptions {
  /** Live box holding the CURRENT chapter's spans — read on every repaint, so
   *  colouring a selection shows immediately without remounting the editor. */
  spansRef: { current: ColourSpan[] };
}

/** Text nodes as passage chunks, in ProseMirror coordinates. Character-for-
 *  character the walk companion-decos.ts uses — identity of the parent block,
 *  not position, decides where a block break falls, so two paragraphs can never
 *  fuse into a match that spans the gap between them. */
function docChunks(doc: PmNode): PassageChunk[] {
  const chunks: PassageChunk[] = [];
  let prevParent: PmNode | null = null;
  doc.descendants((node, pos, parent) => {
    if (!node.isText) return true;
    chunks.push({
      text: node.text ?? "",
      at: pos,
      blockStart: parent !== prevParent,
    });
    prevParent = parent;
    return false;
  });
  return chunks;
}

function build(doc: PmNode, spans: ColourSpan[]): DecorationSet {
  if (!spans.length) return DecorationSet.empty;
  const flat = flatten(docChunks(doc));
  const decos: Decoration[] = [];
  for (const span of spans) {
    for (const r of findPassage(flat, span.quote ?? "")) {
      decos.push(Decoration.inline(r.from, r.to, { class: `ink-${span.ink}` }));
    }
  }
  return DecorationSet.create(doc, decos);
}

export function createColourDecos(opts: ColourDecosOptions): Extension {
  const { spansRef } = opts;
  return Extension.create({
    name: "textColourDecos",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey("textColourDecos"),
          props: {
            decorations(state) {
              return build(state.doc, spansRef.current ?? []);
            },
          },
        }),
      ];
    },
  });
}
