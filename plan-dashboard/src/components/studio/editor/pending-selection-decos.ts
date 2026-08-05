/**
 * pending-selection-decos.ts — tint the ONE passage a reader just highlighted
 * in the Ismaili Scholar Companion panel, while they type a question about it.
 *
 * A ProseMirror decoration, not the CSS Custom Highlight API the panel uses in
 * Read mode: Chromium does not paint `::highlight()` inside `contenteditable`
 * (verified 2026-08-05 — the panel's own DOM Range highlight was invisible in
 * the Edit canvas even though `CSS.highlights` held it correctly), so the Edit
 * canvas needs the SAME mechanism the filed-note tint already uses here —
 * companion-decos.ts — for the same reason: a decoration lives outside the
 * document, so it paints inside contenteditable AND can never reach book.md.
 *
 * Deliberately simpler than companion-decos.ts: this tint is provisional and
 * short-lived (cleared the moment Explain is pressed), so the range is
 * rebuilt from the box on every transaction rather than mapped through edits.
 * A stale position after an unrelated edit elsewhere in the chapter is a
 * acceptable cosmetic miss for something onscreen for a few seconds; the
 * complexity of position-mapping is not.
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PmNode } from "@tiptap/pm/model";

export interface PendingRange {
  from: number;
  to: number;
}

const PENDING_KEY = new PluginKey<DecorationSet>("pendingSelection");

export interface PendingSelectionDecosBag {
  /** The highlighted passage's ProseMirror position span, or null for none.
   *  Mutated by the host; dispatch an empty transaction after changing it to
   *  request a redraw (exactly as `companionNotes` + `markCompanionPassages`
   *  already do for the filed-note tint). */
  rangeRef: { current: PendingRange | null };
}

function build(doc: PmNode, range: PendingRange | null): DecorationSet {
  if (!range) return DecorationSet.empty;
  const max = doc.content.size;
  const from = Math.max(0, Math.min(range.from, max));
  const to = Math.max(from, Math.min(range.to, max));
  if (from === to) return DecorationSet.empty;
  return DecorationSet.create(doc, [
    Decoration.inline(from, to, { class: "cx-pending-hl" }),
  ]);
}

export function createPendingSelectionDecos(
  bag: PendingSelectionDecosBag,
): Extension {
  const { rangeRef } = bag;
  return Extension.create({
    name: "pendingSelection",
    addProseMirrorPlugins() {
      return [
        new Plugin<DecorationSet>({
          key: PENDING_KEY,
          state: {
            init(_config, editorState) {
              return build(editorState.doc, rangeRef.current);
            },
            apply(_tr, _prev, _oldState, newState) {
              return build(newState.doc, rangeRef.current);
            },
          },
          props: {
            decorations(state) {
              return PENDING_KEY.getState(state) ?? DecorationSet.empty;
            },
          },
        }),
      ];
    },
  });
}
