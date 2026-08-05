/**
 * card-heading-buttons.ts — Heading and Subheading as BUTTONS, for the card's
 * one-row toolbar.
 *
 * The package ships headings as a `paragraphFormat` dropdown. A dropdown is the
 * right control for a full-width editor with six levels; in a 330px side panel it
 * cost a whole row and a click to reach the only two levels a card can contain
 * (h3 and h4 — a card sits inside a panel that already has a title). Asif asked
 * for one row and no dropdown, so the two levels become two toggles.
 *
 * Registered through the package's own extension point, like the Composer's
 * Quranic-quotation button: the package knows nothing about what a card is, and
 * the host supplies the meaning.
 */
import { defineButton } from "@asifhussain/prose-editor";
import type { RegisteredButton } from "@asifhussain/prose-editor";

/** Matches the package's 16px stroke grid. */
function headingIcon(label: string): string {
  return (
    '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" ' +
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<path d="M3 3v10"/><path d="M9 3v10"/><path d="M3 8h6"/>' +
    `<text x="11" y="13" font-size="7" stroke="none" fill="currentColor">${label}</text>` +
    "</svg>"
  );
}

function headingButton(
  level: 3 | 4,
  label: string,
  priority: number,
): RegisteredButton {
  return defineButton({
    id: `cardHeading${level}`,
    label,
    tooltip: `${label} — toggles this line`,
    icon: { svg: headingIcon(level === 3 ? "1" : "2") },
    priority,
    isActive: (state) => state.isActive("heading", { level }),
    // Toggle, not set: pressing it on a line that is already this heading takes
    // the line back to body text, which is what a pressed toggle must do.
    run: (api) => void api.chain().focus().toggleHeading({ level }).run(),
  });
}

export function cardHeadingButtons(): RegisteredButton[] {
  return [headingButton(3, "Heading", 20), headingButton(4, "Subheading", 21)];
}
