/**
 * compose-align-command.ts — the Composer's three alignment buttons.
 *
 * Registered through the editor package's extension point, like the verse and
 * colour buttons beside them. They do NOT set a node attribute: markdown has no
 * alignment syntax, so `docToMarkdown` would drop it on the next autosave. The
 * choice is handed to the host, which records it against the PARAGRAPH the
 * cursor is in (`_system/text-align.json`) and repaints from there.
 *
 * Three buttons rather than one dropdown because that is what alignment is
 * everywhere else — three states of one choice, each one click away, each
 * showing whether it is the one in force.
 */
import { defineButton } from "@asifhussain/prose-editor";
import type { RegisteredButton } from "@asifhussain/prose-editor";
import { TEXT_ALIGNMENTS, DEFAULT_TEXT_ALIGN } from "../lib/reader/text-align";
import { TOOLBAR_ICONS } from "./toolbar-icons";

export interface AlignHooks {
  /** Set the paragraph the cursor is in. `left` clears it. */
  onApply: (align: string) => void;
  /** What the cursor's paragraph is set to now, or null when the mapping is
   *  unavailable — in which case the buttons disable rather than lie. */
  getActive: () => string | null;
}

/** One button per alignment, in reading order. */
export function alignButtons(hooks: AlignHooks): RegisteredButton[] {
  return TEXT_ALIGNMENTS.map((a, i) =>
    defineButton({
      id: `align${a.id[0].toUpperCase()}${a.id.slice(1)}`,
      label: a.name,
      tooltip: a.detail,
      icon: TOOLBAR_ICONS[
        `align${a.id[0].toUpperCase()}${a.id.slice(1)}` as keyof typeof TOOLBAR_ICONS
      ],
      priority: 47 + i,
      // Disabled when the paragraph mapping is unavailable — see getActive.
      isEnabled: (state) => state.editable && hooks.getActive() !== null,
      isActive: () => (hooks.getActive() ?? DEFAULT_TEXT_ALIGN) === a.id,
      run: () => hooks.onApply(a.id),
    }),
  );
}
