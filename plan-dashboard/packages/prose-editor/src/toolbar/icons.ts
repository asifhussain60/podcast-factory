/**
 * icons.ts — inline SVG, no icon dependency.
 *
 * A 16px stroke set drawn on the same grid so the bar reads as one thing. These
 * are decorative: every control carries its own accessible name, so the SVGs are
 * `aria-hidden` and a screen reader never sees them.
 */

const svg = (body: string): string =>
  `<svg viewBox="0 0 16 16" width="16" height="16" fill="none" ` +
  `stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ` +
  `stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;

export const ICONS: Readonly<Record<string, string>> = {
  undo: svg('<path d="M3 8h7a3 3 0 1 1 0 6H7"/><path d="M6 5 3 8l3 3"/>'),
  redo: svg('<path d="M13 8H6a3 3 0 1 0 0 6h3"/><path d="M10 5l3 3-3 3"/>'),
  bold: svg(
    '<path d="M4.5 2.5h4a2.75 2.75 0 0 1 0 5.5h-4z"/>' +
      '<path d="M4.5 8h4.75a2.75 2.75 0 0 1 0 5.5H4.5z"/>',
  ),
  italic: svg(
    '<path d="M10 2.5H6.5"/><path d="M9.5 13.5H6"/><path d="M9 2.5 7 13.5"/>',
  ),
  strike: svg(
    '<path d="M2.5 8h11"/>' +
      '<path d="M11.5 4.6C11 3.2 9.7 2.5 8 2.5c-2 0-3.2 1-3.2 2.3 0 1 .7 1.7 2 2.2"/>' +
      '<path d="M4.5 11.2c.4 1.5 1.8 2.3 3.6 2.3 2.1 0 3.4-1 3.4-2.4 0-.8-.4-1.4-1.2-1.9"/>',
  ),
  code: svg('<path d="M5.5 5 2.5 8l3 3"/><path d="M10.5 5l3 3-3 3"/>'),
  link: svg(
    '<path d="M6.8 9.2a2.6 2.6 0 0 0 3.7 0l2-2a2.6 2.6 0 0 0-3.7-3.7l-1 1"/>' +
      '<path d="M9.2 6.8a2.6 2.6 0 0 0-3.7 0l-2 2a2.6 2.6 0 0 0 3.7 3.7l1-1"/>',
  ),
  bulletList: svg(
    '<path d="M6 4h8"/><path d="M6 8h8"/><path d="M6 12h8"/>' +
      '<circle cx="3" cy="4" r=".9" fill="currentColor" stroke="none"/>' +
      '<circle cx="3" cy="8" r=".9" fill="currentColor" stroke="none"/>' +
      '<circle cx="3" cy="12" r=".9" fill="currentColor" stroke="none"/>',
  ),
  orderedList: svg(
    '<path d="M6.5 4h7.5"/><path d="M6.5 8h7.5"/><path d="M6.5 12h7.5"/>' +
      '<path d="M2 3.2h1V6"/><path d="M1.7 6h1.8"/>' +
      '<path d="M1.7 9.6c0-.9 1.8-1 1.8 0 0 .7-1.8 1.3-1.8 2.4h1.9"/>',
  ),
  blockquote: svg(
    '<path d="M3 4.5h3v3.2c0 1.8-1 3-3 3.6"/>' +
      '<path d="M9 4.5h3v3.2c0 1.8-1 3-3 3.6"/>',
  ),
  codeBlock: svg(
    '<rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1.4"/>' +
      '<path d="M6 6.6 4.4 8 6 9.4"/><path d="M10 6.6 11.6 8 10 9.4"/>',
  ),
  horizontalRule: svg(
    '<path d="M2 8h12"/><path d="M4 4h8"/><path d="M4 12h8"/>',
  ),
  clearFormatting: svg(
    '<path d="M6 3h7"/><path d="M9.5 3 7 13"/><path d="M2 11l4 2"/>',
  ),
  fullscreen: svg(
    '<path d="M2.5 6V2.5H6"/><path d="M10 2.5h3.5V6"/>' +
      '<path d="M13.5 10v3.5H10"/><path d="M6 13.5H2.5V10"/>',
  ),
  more: svg(
    '<circle cx="3" cy="8" r="1.1" fill="currentColor" stroke="none"/>' +
      '<circle cx="8" cy="8" r="1.1" fill="currentColor" stroke="none"/>' +
      '<circle cx="13" cy="8" r="1.1" fill="currentColor" stroke="none"/>',
  ),
  chevron: svg('<path d="M4.5 6.5 8 10l3.5-3.5"/>'),
};
