/**
 * align-decos.ts — paint a chapter's stored paragraph alignment in the canvas.
 *
 * A node DECORATION, never a node attribute, for the reason colour-decos.ts is
 * an inline decoration: an attribute is something `docToMarkdown` could be asked
 * to serialize, and book.md has no alignment syntax to serialize it into — so it
 * would be silently dropped on the next autosave. A decoration cannot reach the
 * document at all.
 *
 * HOW A PARAGRAPH IS IDENTIFIED. By its `paraFingerprint`, the same name the
 * sidecar, the print renderer and the Arabic aligner use — but the browser
 * cannot COMPUTE one: the fingerprint is of the raw markdown block, and the
 * canvas holds rendered text. So the keys are the ones the server already ships
 * per chapter (`paraKeys`), matched by POSITION, which is exactly how
 * `applyArabicReveals` maps the same keys onto the read view.
 *
 * Position needs a guard, and it has the same one: the editor's top-level
 * prose blocks are the chapter's prose paragraphs and list blocks PLUS the
 * pipeline's fence markers, which arrive as bare text because TipTap has no
 * comment node. Those are excluded by the shared predicate. If the counts still
 * disagree, the mapping is meaningless and nothing is painted — pointing at the
 * wrong paragraph is worse than pointing at none.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

import { isFenceMarkerText } from "./fence-decos";

export interface AlignDecosOptions {
  /** paraFingerprint -> "center" | "right", for the OPEN chapter. */
  alignRef: { current: Record<string, string> };
  /** The open chapter's ordered prose-block keys, as the server computed them. */
  keysRef: { current: string[] };
}

/**
 * The doc's prose paragraphs, in order, paired with the key at the same index.
 * Empty when the counts disagree — the caller then paints nothing.
 */
export function alignablePositions(
  doc: PmNode,
  keys: string[],
): { from: number; to: number; key: string }[] {
  const found: { from: number; to: number }[] = [];
  doc.forEach((node, offset) => {
    if (
      node.type.name !== "paragraph" &&
      node.type.name !== "bulletList" &&
      node.type.name !== "orderedList"
    )
      return;
    const text = node.textContent.trim();
    if (!text || isFenceMarkerText(text)) return;
    found.push({ from: offset, to: offset + node.nodeSize });
  });
  if (!keys.length || found.length !== keys.length) return [];
  return found.map((p, i) => ({ ...p, key: keys[i] }));
}

function build(
  doc: PmNode,
  align: Record<string, string>,
  keys: string[],
): DecorationSet {
  if (!Object.keys(align).length) return DecorationSet.empty;
  const decos: Decoration[] = [];
  for (const p of alignablePositions(doc, keys)) {
    const want = align[p.key];
    if (want) {
      decos.push(Decoration.node(p.from, p.to, { class: `align-${want}` }));
    }
  }
  return DecorationSet.create(doc, decos);
}

export function createAlignDecos(opts: AlignDecosOptions): Extension {
  const { alignRef, keysRef } = opts;
  return Extension.create({
    name: "textAlignDecos",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey("textAlignDecos"),
          props: {
            decorations(state) {
              return build(
                state.doc,
                alignRef.current ?? {},
                keysRef.current ?? [],
              );
            },
          },
        }),
      ];
    },
  });
}
