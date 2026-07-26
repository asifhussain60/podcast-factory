/**
 * companion-decos.ts — tint a passage that carries a Companion explanation, in
 * the live TipTap edit canvas.
 *
 * Why decorations and not a mark. A mark is part of the document, and anything in
 * the document is serialized by `docToMarkdown()` on the next autosave — a tint
 * modelled as a mark would write highlighting into `book.md` and from there into
 * the printed page. Decorations live outside the document by construction (the
 * same reason figure-decos.ts and fence-decos.ts use them), so the annotation can
 * be visible while you edit and still be incapable of reaching the book.
 *
 * Matching is the shared one (passage-match.ts), fed ProseMirror positions
 * instead of DOM nodes, so the Read view and the Edit canvas can never disagree
 * about which sentence a note is attached to.
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

import type { Box } from "./studio-decos";
import {
  flatten,
  findPassage,
  type PassageChunk,
} from "../../../lib/reader/companion/passage-match";

/** The minimum a note needs to be drawable here. */
export interface CompanionMark {
  id: string;
  quote?: string;
}

export interface CompanionDecosBag {
  /** Notes for the chapter open in the editor. Mutated by the composer, which
   *  dispatches an empty transaction to request a redraw. */
  notesRef: Box<CompanionMark[]>;
}

/** Every text node in the document, as chunks in ProseMirror coordinates. */
function docChunks(doc: PmNode): PassageChunk[] {
  const chunks: PassageChunk[] = [];
  // Identity, not position: a text node's parent is the block it belongs to, and
  // the first text node of a new block is where a block break belongs.
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

export function createCompanionDecos(bag: CompanionDecosBag): Extension {
  const { notesRef } = bag;

  return Extension.create({
    name: "companionPassages",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey("companionPassages"),
          props: {
            decorations(state) {
              const notes = notesRef.current.filter((n) => n.quote);
              if (!notes.length) return DecorationSet.empty;
              const flat = flatten(docChunks(state.doc));
              const decos: Decoration[] = [];
              for (const note of notes) {
                for (const r of findPassage(flat, note.quote ?? "")) {
                  decos.push(
                    Decoration.inline(r.from, r.to, {
                      class: "cx-note-hl",
                      "data-note": note.id,
                      title:
                        "This passage carries a Scholar explanation — click to open it.",
                    }),
                  );
                }
              }
              return DecorationSet.create(state.doc, decos);
            },
          },
        }),
      ];
    },
  });
}
