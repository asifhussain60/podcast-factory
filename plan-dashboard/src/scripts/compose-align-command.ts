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
  /** Set the paragraph the cursor is in. `left` clears it. A no-op when the
   *  cursor is not in one — see getActive. */
  onApply: (align: string) => void;
  /** What the cursor's paragraph is set to now, or null when the cursor is
   *  not in an alignable paragraph or list (inside a quote card, a heading,
   *  a figure caption). */
  getActive: () => string | null;
}

/** One button per alignment, in reading order.
 *
 * ALWAYS ENABLED while the editor is editable (Asif, 2026-08-14, reverses the
 * original "disabled when the paragraph mapping is unavailable" rule) — a
 * normal editor's alignment controls do not grey out depending on where the
 * cursor happens to be, and greying out read as broken rather than as a
 * boundary. A click with the cursor somewhere `getActive` cannot map (a quote
 * card, a heading) is a quiet no-op: `onApply` already returns early when
 * there is no key to write against, and quote cards are a deliberately
 * un-alignable case (see their own CSS: every card's Arabic/translation line
 * is pinned centered by design, not by the absence of this control). The
 * pressed-state still falls back to `DEFAULT_TEXT_ALIGN` on null, so a card
 * shows "Left" pressed rather than nothing — an honest default, not a claim
 * that the card is actually left-aligned. */
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
      isEnabled: (state) => state.editable,
      isActive: () => (hooks.getActive() ?? DEFAULT_TEXT_ALIGN) === a.id,
      run: () => hooks.onApply(a.id),
    }),
  );
}
