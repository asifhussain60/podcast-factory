/**
 * store.ts — reading and writing an EXISTING book's settings.
 *
 * The Intake wizard commissions new content; this module is what lets the same
 * form load a book that already exists and save corrections back. There is no
 * database behind these settings: `unit_detail` in the Library's D1 has columns
 * for seven of them and is written one-way by the publish step, so the files on
 * disk are the store, and the Library picks changes up at the next publish.
 *
 * Two files per book, and which one a field lives in is not guessable — hence
 * FIELD_FILES below, the single place that mapping is written down.
 *
 * READS parse the YAML (safe, and it has to cope with nesting). WRITES patch
 * the file LINE BY LINE, never parse-and-redump, for the reason api/studio/
 * book-meta.ts already gives: these files carry comments, and nineteen of them
 * carry keys this form has never heard of (translation_policy,
 * notebooklm_settings, source_tradition). A redump would silently discard both.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import yaml from "js-yaml";

/** Which file a field is stored in. */
export type StoreFile = "meta" | "series";

export const META_FILE = "meta.yml";
export const SERIES_FILE = join("_system", "series-config.yaml");

/**
 * field key -> where it lives, and under which YAML key.
 *
 * `path` is the key IN THE FILE, which is not always the form's field key:
 * the doctrinal fields are nested, and the podcast conversation style is
 * `conversation_style` in eight books and `host_dynamic` in others.
 */
export interface FieldLocation {
  file: StoreFile;
  /** Dotted path within the file. One level of nesting is supported. */
  path: string;
  /** Additional keys to read from when `path` is absent, in order. */
  readAlso?: string[];
}

export const FIELD_FILES: Record<string, FieldLocation> = {
  // ── meta.yml — what the work IS ──
  title: { file: "meta", path: "title" },
  title_arabic: { file: "meta", path: "title_arabic" },
  title_english: { file: "meta", path: "title_english" },
  original_title: { file: "meta", path: "original_title" },
  author: { file: "meta", path: "author" },
  short_name: { file: "meta", path: "short_name" },
  study_track: { file: "meta", path: "study_track" },
  archetype: { file: "meta", path: "archetype" },
  content_level: { file: "meta", path: "content_level" },
  density: { file: "meta", path: "density" },
  category: { file: "meta", path: "category" },
  doctrinal_school: { file: "meta", path: "doctrinal_context.school" },
  doctrinal_period: { file: "meta", path: "doctrinal_context.period" },
  doctrinal_genre: { file: "meta", path: "doctrinal_context.genre" },
  enable_book_branch: { file: "meta", path: "series.enable_book_branch" },
  enable_slide_decks: { file: "meta", path: "series.enable_slide_decks" },

  // ── series-config.yaml — how it is PRODUCED ──
  content_profile: { file: "series", path: "content_profile" },
  source_medium: { file: "series", path: "source_medium" },
  source_language: { file: "series", path: "source_language" },
  source_fidelity: { file: "series", path: "source_fidelity" },
  narrative_frame: { file: "series", path: "narrative_frame" },
  narrator_subject: { file: "series", path: "narrator_subject" },
  deliverable_mode: { file: "series", path: "deliverable_mode" },
  book_voice: { file: "series", path: "book_voice" },
  book_augmentation: { file: "series", path: "book_augmentation" },
  book_visuals: { file: "series", path: "book_visuals" },
  autonomy: { file: "series", path: "autonomy" },
  audience_profile: { file: "series", path: "audience_profile" },
  // Written as conversation_style by intake_launch, but eight older books spell
  // it host_dynamic. Read either; write back to whichever the book already has.
  host_dynamic: {
    file: "series",
    path: "conversation_style",
    readAlso: ["host_dynamic"],
  },
  length_tier: { file: "series", path: "length_tier" },
  video_style: { file: "series", path: "video_style" },
  episode_planning_mode: { file: "series", path: "episode_planning_mode" },
  slide_deck_mode: { file: "series", path: "slide_deck_mode" },
  volume: { file: "series", path: "volume" },
};

/**
 * Fields that describe WHERE a book lives rather than what it is. Shown so the
 * picture is complete, never writable here: the content profile decides the
 * bucket, which is the folder path AND the git branch, and the folder name is
 * the book's identity with its own guarded rename flow.
 */
export const LOCKED_FOR_EXISTING: ReadonlySet<string> = new Set([
  "slug",
  "content_family",
  "content_profile",
  "source_medium",
]);

function filePath(dir: string, file: StoreFile): string {
  return join(dir, file === "meta" ? META_FILE : SERIES_FILE);
}

function dig(doc: unknown, path: string): unknown {
  let cur: unknown = doc;
  for (const part of path.split(".")) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

/** A YAML scalar as the form's string value. Objects/arrays are not editable. */
function asFormValue(v: unknown): string | undefined {
  if (v === null || v === undefined) return undefined;
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return String(v);
  if (typeof v === "string") return v;
  return undefined;
}

export interface LoadedBook {
  slug: string;
  bucket: string;
  dir: string;
  values: Record<string, string>;
  /** Files that exist on disk. A field whose file is missing cannot be saved. */
  present: Record<StoreFile, boolean>;
}

export async function loadBook(
  slug: string,
  bucket: string,
  dir: string,
): Promise<LoadedBook> {
  const docs: Record<StoreFile, unknown> = { meta: null, series: null };
  const present: Record<StoreFile, boolean> = { meta: false, series: false };

  for (const file of ["meta", "series"] as StoreFile[]) {
    const p = filePath(dir, file);
    if (!existsSync(p)) continue;
    present[file] = true;
    try {
      docs[file] = yaml.load(await readFile(p, "utf8"));
    } catch {
      // A file we cannot parse is reported as absent rather than half-read: a
      // partial load would show blanks that look like deliberate empties.
      present[file] = false;
    }
  }

  const values: Record<string, string> = { slug };
  for (const [key, loc] of Object.entries(FIELD_FILES)) {
    const doc = docs[loc.file];
    let raw = dig(doc, loc.path);
    if (raw === undefined) {
      for (const alt of loc.readAlso ?? []) {
        raw = dig(doc, alt);
        if (raw !== undefined) break;
      }
    }
    const v = asFormValue(raw);
    if (v !== undefined) values[key] = v;
  }
  return { slug, bucket, dir, values, present };
}

/** Quote a scalar only when YAML would otherwise mis-read it. Mirrors book-meta.ts. */
function yamlScalar(value: string): string {
  if (value === "") return '""';
  if (/[:#&*!|>'"%@`{}[\],]/.test(value) || /^\s|\s$/.test(value)) {
    return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  }
  return value;
}

/**
 * Set one dotted key in a YAML file by patching LINES, so comments, key order
 * and every key this form does not know about survive untouched.
 *
 * Supports a top-level key and one level of nesting. A nested key is written
 * inside its parent's indented block; if the parent is absent the whole block
 * is appended, because a child cannot be written without one.
 */
export function patchYamlLines(
  original: string,
  path: string,
  value: string,
): string {
  // A file that ended with a newline must still end with one. Appending after
  // the trailing empty element that split() produces would drop it, and git
  // then reports "\\ No newline at end of file" on every later diff of a file
  // this touched once.
  const endedWithNewline = original.endsWith("\n");
  const finish = (out: string[]) => {
    let text = out.join("\n");
    if (endedWithNewline && !text.endsWith("\n")) text += "\n";
    return text;
  };

  const lines = original.split("\n");
  const parts = path.split(".");

  /** Index just past the last line with content, so appends land before the
   *  trailing blank(s) rather than after them. */
  const contentEnd = () => {
    let i = lines.length;
    while (i > 0 && lines[i - 1].trim() === "") i -= 1;
    return i;
  };

  if (parts.length === 1) {
    const re = new RegExp(`^${parts[0]}:\\s*.*$`);
    const idx = lines.findIndex((ln) => re.test(ln));
    const line = `${parts[0]}: ${yamlScalar(value)}`;
    if (idx !== -1) lines[idx] = line;
    else lines.splice(contentEnd(), 0, line);
    return finish(lines);
  }

  const [parent, child] = parts;
  const parentRe = new RegExp(`^${parent}:\\s*$`);
  const pIdx = lines.findIndex((ln) => parentRe.test(ln));
  if (pIdx === -1) {
    lines.splice(
      contentEnd(),
      0,
      `${parent}:`,
      `  ${child}: ${yamlScalar(value)}`,
    );
    return finish(lines);
  }

  // The parent's block runs until the next line that is neither indented nor blank.
  let end = pIdx + 1;
  while (
    end < lines.length &&
    (lines[end].trim() === "" || /^\s/.test(lines[end]))
  ) {
    end += 1;
  }
  const childRe = new RegExp(`^(\\s+)${child}:\\s*.*$`);
  for (let i = pIdx + 1; i < end; i += 1) {
    const m = lines[i].match(childRe);
    if (m) {
      lines[i] = `${m[1]}${child}: ${yamlScalar(value)}`;
      return finish(lines);
    }
  }
  // Absent: insert at the end of the block, matching the block's indent.
  const indent = lines[pIdx + 1]?.match(/^(\s+)/)?.[1] ?? "  ";
  let insertAt = end;
  while (insertAt > pIdx + 1 && lines[insertAt - 1].trim() === "")
    insertAt -= 1;
  lines.splice(insertAt, 0, `${indent}${child}: ${yamlScalar(value)}`);
  return finish(lines);
}

export interface SaveResult {
  written: { field: string; file: StoreFile; path: string; value: string }[];
  skipped: { field: string; reason: string }[];
  /** Files this save had to create because the book did not have them. */
  created?: string[];
}

/**
 * Header for a `series-config.yaml` this module creates.
 *
 * Only ever written when the file is ABSENT, so it cannot displace a comment
 * anyone wrote. It says where the file came from because the other way a book
 * gets one is `intake_launch.py::_write_series_config`, and a reader comparing
 * two books should not have to guess which path produced which.
 */
const SERIES_HEADER = [
  "# series-config.yaml — the pipeline settings for this book.",
  "#",
  "# Created by the Intake form when settings were saved for a book that had",
  "# none. A book scaffolded by hand never gets one (only intake_launch.py's",
  "# _write_series_config does), and half the form's fields live in this file —",
  "# so without it those saves were silently dropped.",
  "",
].join("\n");

/** Apply changed fields to the right file each. Only listed fields are touched. */
export async function saveBook(
  dir: string,
  changes: Record<string, string>,
): Promise<SaveResult> {
  const written: SaveResult["written"] = [];
  const skipped: SaveResult["skipped"] = [];
  const byFile: Record<
    StoreFile,
    { field: string; path: string; value: string }[]
  > = {
    meta: [],
    series: [],
  };

  for (const [field, value] of Object.entries(changes)) {
    if (LOCKED_FOR_EXISTING.has(field)) {
      skipped.push({ field, reason: "structural — not editable here" });
      continue;
    }
    const loc = FIELD_FILES[field];
    if (!loc) {
      skipped.push({ field, reason: "not a stored setting" });
      continue;
    }
    byFile[loc.file].push({ field, path: loc.path, value });
  }

  const created: string[] = [];

  for (const file of ["meta", "series"] as StoreFile[]) {
    const pending = byFile[file];
    if (pending.length === 0) continue;
    const p = filePath(dir, file);
    if (!existsSync(p)) {
      // A missing series-config.yaml is CREATED, not reported as an obstacle.
      // It is optional by construction — the pipeline reads it with defaults
      // when absent, and only intake_launch.py writes one — so a book scaffolded
      // by any other route has none, and eighteen of this form's ~34 fields live
      // in it. Skipping meant saving those fields appeared to work and silently
      // did nothing (source_language and video_style, reported 2026-08-30).
      //
      // meta.yml is NOT created the same way: it is the book's identity, every
      // real book has one, and writing a fresh one from a handful of patched
      // fields would turn "you pointed at the wrong folder" into a new file
      // that makes the wrong folder look like a book.
      if (file === "meta") {
        for (const c of pending) {
          skipped.push({
            field: c.field,
            reason: `this book has no ${META_FILE}`,
          });
        }
        continue;
      }
      await mkdir(dirname(p), { recursive: true });
      await writeFile(p, SERIES_HEADER, "utf8");
      created.push(SERIES_FILE);
    }
    let text = await readFile(p, "utf8");
    for (const c of pending) {
      text = patchYamlLines(text, c.path, c.value);
      written.push({ field: c.field, file, path: c.path, value: c.value });
    }
    await writeFile(p, text, "utf8");
  }

  return created.length ? { written, skipped, created } : { written, skipped };
}
