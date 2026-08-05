/**
 * compose-colour-command.ts — the Composer's text-colour button.
 *
 * Registered through the editor package's extension point, like the Qur'anic
 * quotation button beside it. The package knows nothing about this book format
 * and must not; what it provides is the registration surface.
 *
 * The button does NOT apply a mark. There is no colour syntax in markdown, so a
 * mark would be dropped by `docToMarkdown` on the next autosave — instead the
 * chosen colour is handed to the host, which records the SELECTED TEXT verbatim
 * in `_system/text-colour.json` and repaints the canvas from there. The colour
 * therefore survives a save because it was never in the document to lose.
 *
 * A selection shorter than the matcher's floor is refused rather than stored: a
 * three-character quote cannot be re-found unambiguously, so a record of one
 * would be a colour that never reappears and nobody could explain.
 */
import { defineButton } from "@asifhussain/prose-editor";
import type { RegisteredButton } from "@asifhussain/prose-editor";
import { openPalette } from "./ink-palette";

/** Below this the shared matcher refuses to guess — see passage-match. */
export const MIN_COLOURABLE = 4;

/** What the host does with a decision. `ink: null` means "remove the colour". */
export type ApplyColour = (quote: string, ink: string | null) => void;

const PALETTE_ICON =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="16" ' +
  'height="16" fill="currentColor" aria-hidden="true" focusable="false">' +
  '<path d="M96 32C43 32 0 75 0 128L0 384c0 53 43 96 96 96l320 0c53 0 96-43 ' +
  "96-96l0-256c0-53-43-96-96-96L96 32zM64 416l384 0 0 32L64 448l0-32zM246 " +
  "116c-4-9-13-15-23-15s-19 6-23 15l-72 160c-5 12 0 26 12 31s26 0 31-12l10-23 " +
  '84 0 10 23c5 12 19 17 31 12s17-19 12-31l-72-160zm-42 108l19-43 19 43-38 0z"/>' +
  "</svg>";

/**
 * Build the button. The host supplies `onApply` (which knows the chapter and the
 * API) and `getActive` (the ink already on the selection, so the palette can
 * show which one is set and offer to take it off).
 */
export function textColourButton(opts: {
  onApply: ApplyColour;
  getActive: () => string | null;
}): RegisteredButton {
  return defineButton({
    id: "textColour",
    label: "Text colour",
    tooltip: "Colour the selected text",
    icon: { svg: PALETTE_ICON },
    priority: 46,
    ariaHasPopup: "menu",
    isEnabled: (state) => state.editable && !state.empty,
    isActive: () => Boolean(opts.getActive()),
    run: (api) => {
      const quote = api.getSelectedText().trim();
      if (quote.length < MIN_COLOURABLE) return;
      openPalette({
        returnFocusTo: api.editor.view.dom as HTMLElement,
        anchor: document.querySelector('[data-rte-id="textColour"]'),
        active: opts.getActive(),
        choose: (ink) => opts.onApply(quote, ink),
      });
    },
  });
}
