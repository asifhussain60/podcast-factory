/**
 * image-layout.mjs — read/write a book's per-image resize/align choices.
 *
 * Same reasoning as text-align.mjs and quote-groups.mjs: book.md is never
 * touched. Markdown has no sizing syntax, the print renderer escapes raw
 * HTML, and inventing one would put new delimiters into a file every Python
 * phase reads as text. So the choice lives in `_system/image-layout.json`
 * and is applied at RENDER time, in every renderer that draws an image.
 *
 * THE KEY IS THE IMAGE'S OWN `src`, verbatim — not a fingerprint, not a
 * position index. Unlike a text paragraph (which needs `paraFingerprint`
 * because plain prose has no other stable name) or a quote fragment (keyed
 * by its own first line, for the same reason), an image already carries a
 * name that is unique within a chapter in every book on disk today: the path
 * to the file itSELF. Reusing it means no new identity scheme, and — unlike
 * `paraFingerprint` — a plain string needs no hash implementation duplicated
 * into the browser bundle, which is exactly the mistake an earlier draft of
 * quote-groups.mjs made and had to be corrected out of (see that file's own
 * header). `src` is read identically by every renderer already, with zero
 * new code.
 *
 * SCHEMA: { chapterKey: { src: { height_px, align } } }. `height_px` is a
 * plain pixel integer, not a percentage — v1 stored `width_pct`, a percentage
 * of whatever column happened to contain the image, which made two images of
 * different shapes at the "same" width render at two different heights, and
 * made the SAME width_pct render at a different on-screen height depending on
 * the window's size. Asif's own resizing on 2026-08-14 (two images tuned by
 * eye to look the same height) came out 375px and 257px apart under v1 for
 * exactly that reason. Height is what a reader's eye actually judges "the
 * same size" by, and it is architecturally stable in a way a width-of-a-
 * shifting-column percentage never was: fixed regardless of column width, and
 * the image's own aspect ratio (the browser's, not ours to compute) supplies
 * the width for free. `align` is "left" | "center" | "right", unchanged.
 * Neither is stored when it would be the default (`height_px: 350`, `align:
 * "center"`), so an unedited image writes nothing and a book with no sidecar
 * renders byte-identical to before this existed.
 */
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";

const SCHEMA = "book.image-layout/v2";
export const ALIGN_IDS = ["left", "center", "right"];
export const DEFAULT_ALIGN = "center";
export const DEFAULT_HEIGHT_PX = 350;
export const MIN_HEIGHT_PX = 60;
export const MAX_HEIGHT_PX = 1200;

function normalizeEntry(raw) {
  const height = Number(raw?.height_px);
  const align = raw?.align;
  const out = {};
  if (
    Number.isInteger(height) &&
    height >= MIN_HEIGHT_PX &&
    height <= MAX_HEIGHT_PX &&
    height !== DEFAULT_HEIGHT_PX
  )
    out.height_px = height;
  if (ALIGN_IDS.includes(align) && align !== DEFAULT_ALIGN) out.align = align;
  return out;
}

/**
 * `_system/image-layout.json` → { chapterKey: { src: {height_px?, align?} } }.
 * Unreadable, absent or malformed yields {} — an edition renders every image
 * at its default fixed height and centering rather than failing to render.
 * A v1 file (schema string aside, ANY file whose entries carry `width_pct`
 * instead of `height_px`) reads as {} too: `normalizeEntry` only recognizes
 * `height_px`, so a stale percentage is dropped as absent rather than
 * misread as a pixel count — the one outcome worse than losing a saved size
 * is applying last version's number under this version's unit.
 */
export function readImageLayout(bookDir) {
  const p = path.join(bookDir, "_system", "image-layout.json");
  if (!existsSync(p)) return {};
  try {
    const raw = JSON.parse(readFileSync(p, "utf-8"));
    const out = {};
    for (const [chapter, images] of Object.entries(raw?.chapters ?? {})) {
      if (!images || typeof images !== "object") continue;
      const kept = {};
      for (const [src, decl] of Object.entries(images)) {
        const entry = normalizeEntry(decl);
        if (Object.keys(entry).length) kept[String(src).trim()] = entry;
      }
      if (Object.keys(kept).length) out[chapter] = kept;
    }
    return out;
  } catch {
    return {};
  }
}

/** Every chapter's declarations flattened into ONE src -> {height_px?, align?}
 *  map. Safe to flatten for the same reason quoteKind's flattening is: an
 *  `src` is the image's own path, so two chapters can only collide by
 *  embedding the literal same file — in which case they want the same size. */
export function flattenImageLayout(byChapter) {
  const flat = {};
  for (const images of Object.values(byChapter ?? {}))
    Object.assign(flat, images);
  return flat;
}

/**
 * Write (or clear) one image's layout. Read-modify-MERGE, mirroring
 * writeQuoteGroup — the Composer's resize handle calls this once per drag
 * release and the align toolbar calls it once per click, independently, so
 * this must merge onto whatever the OTHER control already saved rather than
 * replacing the whole entry — a click on "align left" must not silently
 * erase a resize made a minute earlier. Only a field actually PASSED
 * (`height_px` or `align`, not merely present-but-undefined) overrides the
 * stored value; omitting one leaves it as it was.
 *
 * Passing both `height_px: 350` and `align: "center"` (the defaults)
 * together clears the entry entirely — a resize back to the default is
 * indistinguishable from never having been set, which is the point: nothing
 * here can drift into recording redundant state.
 */
export function writeImageLayout(
  bookDir,
  chapterKey,
  src,
  { height_px, align } = {},
) {
  const chapter = String(chapterKey ?? "").trim();
  const key = String(src ?? "").trim();
  if (!chapter || !key) throw new Error("chapterKey and src are required");
  const dir = path.join(bookDir, "_system");
  const p = path.join(dir, "image-layout.json");
  const store = { schema: SCHEMA, chapters: readImageLayout(bookDir) };
  const existing = store.chapters[chapter]?.[key] ?? {};
  const merged = {
    height_px: height_px !== undefined ? height_px : existing.height_px,
    align: align !== undefined ? align : existing.align,
  };
  const entry = normalizeEntry(merged);
  if (Object.keys(entry).length) {
    store.chapters[chapter] = {
      ...(store.chapters[chapter] ?? {}),
      [key]: entry,
    };
  } else if (store.chapters[chapter]) {
    delete store.chapters[chapter][key];
    if (!Object.keys(store.chapters[chapter]).length)
      delete store.chapters[chapter];
  }
  mkdirSync(dir, { recursive: true });
  writeFileSync(p, JSON.stringify(store, null, 2) + "\n", "utf-8");
  return store;
}
