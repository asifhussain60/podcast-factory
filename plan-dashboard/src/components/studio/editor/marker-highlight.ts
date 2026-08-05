/**
 * marker-highlight.ts — TipTap extension rendering inline reference markers
 * (Hadith/Works highlight + chip pills). Extracted from StudioEditor.tsx
 * (R2 pass 1a — mechanical, verbatim). Quran verse refs stay FC-1 chips in
 * StudioDecos, not here.
 */
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

import { MARKER_PATTERNS } from "./studio-editor-constants";

// Hadith + Works: inline highlight + visible chip pill. Quran verse refs become FC-1 chips.
export const MarkerHighlight = Extension.create({
  name: "markerHighlight",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("markerHighlight"),
        props: {
          decorations(state) {
            const decos: Decoration[] = [];
            state.doc.descendants((node, pos) => {
              if (!node.isText || !node.text) return;
              for (const { re, cls, chip } of MARKER_PATTERNS) {
                if (cls === "mk-quran") continue; // handled as FC-1 chips
                re.lastIndex = 0;
                let m: RegExpExecArray | null;
                while ((m = re.exec(node.text))) {
                  const from = pos + m.index;
                  const to = from + m[0].length;
                  decos.push(
                    Decoration.inline(from, to, { class: `mk ${cls}` }),
                  );
                  if (chip) {
                    const label = chip;
                    const kind = cls.replace("mk-", "");
                    decos.push(
                      Decoration.widget(
                        to,
                        () => {
                          const span = document.createElement("span");
                          span.className = `mk-chip mk-chip--${kind}`;
                          span.textContent = label;
                          span.setAttribute("aria-label", label);
                          return span;
                        },
                        { side: 1, key: `mkchip-${from}` },
                      ),
                    );
                  }
                }
              }
            });
            return DecorationSet.create(state.doc, decos);
          },
        },
      }),
    ];
  },
});
