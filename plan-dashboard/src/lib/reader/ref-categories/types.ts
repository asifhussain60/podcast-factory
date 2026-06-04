/**
 * Pluggable reference-category registry types.
 *
 * Each RefCategory describes ONE class of inline reference (Quran, Hadith,
 * Arabic transliteration, etymology, ...). The registry abstraction means
 * adding a new category later (e.g. etymology) requires one file in
 * `builtin/` and one line in `index.ts` — nothing else changes.
 *
 * See SPEC.md §"Marking strategy — pluggable category registry".
 */

export interface RefTypography {
  /** CSS font-family stack — full string, e.g. `"EB Garamond", Georgia, serif`. */
  fontFamily: string;
  fontWeight?: number;
  fontStyle?: 'normal' | 'italic';
  letterSpacing?: string;
  smallCaps?: boolean;
}

export interface RefMatch {
  /** Character offset (inclusive) into the HTML string passed to detect(). */
  start: number;
  /** Character offset (exclusive). */
  end: number;
  /** Canonical value carried on the rendered span as `data-ref-value`. */
  value: string;
  /** Optional extra attributes — emitted as `data-{key}`. */
  attrs?: Record<string, string>;
}

export interface DetectContext {
  /** Whole HTML the detector was given. */
  html: string;
}

export interface RefCategory {
  /** Stable identifier; becomes `data-ref-type="{id}"` and the `ref-{id}` CSS class. */
  id: string;
  /** Human-readable label, used in toolbar filter chips and counts. */
  label: string;
  /** Gutter glyph icon (an emoji or short string). */
  glyph: string;
  /** Tailwind color token — `blue`, `amber`, `green`, `purple`, ... */
  colorToken: string;
  /** Per-category typography assignment. */
  typography: RefTypography;
  /** Keyboard shortcuts for next/prev navigation. */
  shortcuts: { next: string; prev: string };
  /** Higher priority wins when matches overlap. Default 0. */
  priority?: number;
  /** Default-enabled if no user pref overrides. */
  enabledByDefault: boolean;
  /** Detection function — returns matches against the input HTML string. */
  detect: (html: string, context: DetectContext) => RefMatch[];
}

export interface RegistryValidationIssue {
  level: 'warn' | 'error';
  message: string;
}
