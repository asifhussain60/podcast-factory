/**
 * read-along-decos.ts — light the paragraph the recording is speaking.
 *
 * The Composer already paints passages for other reasons — a Companion card's
 * sentence, a reference marker, a fence — and this is that same mechanism driven
 * by the clock instead of by the document.
 *
 * HOW A PARAGRAPH IS FOUND, and why it is checked afterwards. A cue carries the
 * index of the block it was spoken from, counted over the chapter's markdown
 * blocks. The editor holds those same blocks as the document's top-level nodes,
 * so the index finds the paragraph directly. But the two counts are produced by
 * different code on different sides of the pipeline, and a list, a figure or a
 * comment is exactly the kind of thing one might count and the other not.
 *
 * So the index LOCATES and the text CONFIRMS: the cue's own words are compared
 * with the paragraph's before anything is painted, and a poor match paints
 * NOTHING. That is the rule this repo already applies to a Companion card whose
 * quote cannot be found — an explanation attached to the wrong passage of a
 * religious text is worse than no explanation — and it is the same judgement
 * here, where a paragraph lit while a different one is spoken is the whole
 * failure the timing gate exists to prevent.
 *
 * A decoration never touches the document, so nothing here can reach book.md
 * through the next autosave.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import type { EditorState, Transaction } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PMNode } from "@tiptap/pm/model";

export const readAlongKey = new PluginKey<number>("readAlong");

/** Words worth comparing: the short ones agree by accident. */
function words(text: string): Set<string> {
  return new Set((text.toLowerCase().match(/[a-z]{4,}/g) ?? []).slice(0, 40));
}

/**
 * Is this paragraph the one the cue was spoken from?
 *
 * Deliberately loose. A cue's text has had its Arabic script and its markdown
 * removed on the way to a speech engine, so it is never character-identical to
 * the paragraph in the editor; what it keeps is the English wording. Half the
 * cue's distinctive words appearing in the paragraph is strong evidence, and
 * two different paragraphs of the same chapter do not clear it by chance.
 *
 * A cue with no comparable words at all — a line of pure Arabic, a numeral —
 * is ACCEPTED on the index alone: there is nothing to check it with, and
 * refusing every such paragraph would blank the highlight through passages of
 * scripture, which is where a reader most wants to keep their place.
 */
export function blockMatches(blockText: string, cueText: string): boolean {
  const cue = words(cueText);
  if (cue.size === 0) return true;
  const block = words(blockText);
  let shared = 0;
  for (const w of cue) if (block.has(w)) shared += 1;
  return shared / cue.size >= 0.5;
}

export interface ReadAlongTarget {
  /** Index of the top-level block the recording is speaking, or -1 for none. */
  blockIndex: number;
  /** What that cue said, used to confirm the block before painting it. */
  text: string;
}

const NONE: ReadAlongTarget = { blockIndex: -1, text: "" };

/** Where in the document the block sits, or null when there is no such block. */
function blockAt(
  doc: PMNode,
  index: number,
): { node: PMNode; pos: number } | null {
  if (index < 0 || index >= doc.childCount) return null;
  let pos = 0;
  for (let i = 0; i < index; i += 1) pos += doc.child(i).nodeSize;
  return { node: doc.child(index), pos };
}

/**
 * How far from the hint a paragraph may be found. The two counts drift by a node
 * here and a node there — an image, a fence marker, a figure the editor holds and
 * the markdown split never produced — and the drift accumulates down a chapter.
 * Measured on `purification-of-the-heart`: 102 editor nodes against 94 timed
 * blocks by the end of one chapter, which left the index alone right for 8 of
 * them. Bounded rather than unbounded so a paragraph is never found halfway
 * across the chapter from where it was said — that is how a search turns a small
 * offset into a confident wrong answer.
 */
const SEARCH_RADIUS = 24;

/**
 * The block this cue was spoken from: the hint if it holds, else the nearest
 * block that does, else none.
 *
 * Searching OUTWARD from the hint keeps the answer near where the recording says
 * it should be while absorbing the drift, and returning -1 when nothing matches
 * keeps the original guarantee exactly: rather than light the wrong paragraph,
 * light none.
 */
export function resolveBlock(
  doc: PMNode,
  hint: number,
  cueText: string,
): number {
  const inRange = (i: number) => i >= 0 && i < doc.childCount;
  if (inRange(hint) && blockMatches(doc.child(hint).textContent, cueText))
    return hint;
  for (let step = 1; step <= SEARCH_RADIUS; step += 1) {
    for (const i of [hint + step, hint - step]) {
      if (inRange(i) && blockMatches(doc.child(i).textContent, cueText))
        return i;
    }
  }
  return -1;
}

function decorate(state: EditorState, target: ReadAlongTarget): DecorationSet {
  const found = blockAt(
    state.doc,
    resolveBlock(state.doc, target.blockIndex, target.text),
  );
  if (!found) return DecorationSet.empty;
  return DecorationSet.create(state.doc, [
    Decoration.node(found.pos, found.pos + found.node.nodeSize, {
      class: "cx-read-along",
    }),
  ]);
}

export const ReadAlong = Extension.create({
  name: "readAlong",
  addProseMirrorPlugins() {
    return [
      new Plugin<ReadAlongTarget>({
        key: readAlongKey as unknown as PluginKey<ReadAlongTarget>,
        state: {
          init: () => NONE,
          apply: (tr: Transaction, value: ReadAlongTarget) =>
            (tr.getMeta(readAlongKey) as ReadAlongTarget | undefined) ?? value,
        },
        props: {
          decorations(state) {
            const target =
              (this as unknown as Plugin<ReadAlongTarget>).getState(state) ??
              NONE;
            if (target.blockIndex < 0) return DecorationSet.empty;
            return decorate(state, target);
          },
        },
      }),
    ];
  },
});

/** Move the highlight. Passing blockIndex -1 clears it. */
export function setReadAlongTarget(
  editor: { view: { dispatch: (tr: Transaction) => void; state: EditorState } },
  target: ReadAlongTarget,
): void {
  const { state, dispatch } = editor.view;
  dispatch(state.tr.setMeta(readAlongKey, target));
}

/**
 * The paragraph currently painted, for scroll-follow.
 *
 * Found by the class the decoration puts there rather than by index, because
 * the index the caller has is a HINT and `resolveBlock` may have landed
 * elsewhere. Asking the DOM what was painted cannot disagree with what was
 * painted; recomputing the index here could, and would scroll to a paragraph
 * other than the lit one.
 */
export function readAlongElement(view: {
  dom: HTMLElement;
}): HTMLElement | null {
  return view.dom.querySelector<HTMLElement>(".cx-read-along");
}
