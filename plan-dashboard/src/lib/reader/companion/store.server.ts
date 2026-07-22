/**
 * companion/store.server.ts — the on-disk persistence for Companion notes.
 *
 * SERVER ONLY (uses node:fs). Never import from a browser bundle — the API route
 * api/studio/companion-notes.ts is the boundary.
 *
 * Storage: one JSON file per chapter at
 *   content/<Bucket>/<slug>/_system/companion-notes/<chapter>.json
 * JSON (not YAML) so the Python pipeline can read it too, mirroring editorial.ts.
 * _system/ is git-tracked (only _system/scratchpad and _system/drafts are ignored),
 * so these notes commit and sync across machines — while staying out of book.md and
 * the generated PDF entirely.
 */
import {
  readFileSync,
  writeFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { randomUUID } from "node:crypto";
import { findContentDirSync, contentDir } from "../../content-paths";
import { CHAPTER_KEY_RE } from "./keys";
import type {
  CompanionChapterDoc,
  CompanionChapterSummary,
  CompanionNote,
  CompanionNoteInput,
} from "./types";

/** Same resolver + fallback the editorial cockpit uses (bucket-first, legacy fallback). */
function bookBaseDir(slug: string): string {
  return findContentDirSync(slug) ?? contentDir(slug);
}

function companionDir(slug: string): string {
  return join(bookBaseDir(slug), "_system", "companion-notes");
}

/** Path for a chapter file, with a hard traversal guard on the key. */
function chapterPath(slug: string, chapter: string): string {
  if (!CHAPTER_KEY_RE.test(chapter)) {
    throw new Error(`invalid chapter key: ${chapter}`);
  }
  return join(companionDir(slug), `${chapter}.json`);
}

function nowIso(): string {
  return new Date().toISOString().replace(/\.\d+Z$/, "Z");
}

function emptyDoc(slug: string, chapter: string): CompanionChapterDoc {
  return { slug, chapter, notes: [], updatedAt: null };
}

/** Read all notes for one chapter (empty doc if none stored yet). */
export function readChapter(
  slug: string,
  chapter: string,
): CompanionChapterDoc {
  const p = chapterPath(slug, chapter);
  if (!existsSync(p)) return emptyDoc(slug, chapter);
  try {
    const parsed = JSON.parse(readFileSync(p, "utf8")) as CompanionChapterDoc;
    return {
      slug,
      chapter,
      notes: Array.isArray(parsed.notes) ? parsed.notes : [],
      updatedAt: parsed.updatedAt ?? null,
    };
  } catch {
    return emptyDoc(slug, chapter);
  }
}

function writeChapter(doc: CompanionChapterDoc): CompanionChapterDoc {
  const p = chapterPath(doc.slug, doc.chapter);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(doc, null, 2) + "\n", "utf8");
  return doc;
}

/**
 * Create (no id) or update (matching id) one note. Returns the saved note.
 * Unknown id on update is treated as a create so a stale client never silently loses data.
 */
export function upsertNote(
  slug: string,
  chapter: string,
  input: CompanionNoteInput,
): { doc: CompanionChapterDoc; note: CompanionNote } {
  const body = (input.body ?? "").trim();
  if (!body) throw new Error("note body is required");
  const doc = readChapter(slug, chapter);
  const ts = nowIso();
  const existing = input.id
    ? doc.notes.find((n) => n.id === input.id)
    : undefined;

  let note: CompanionNote;
  if (existing) {
    note = {
      ...existing,
      kind: input.kind || existing.kind,
      body,
      anchor: input.anchor?.trim() || undefined,
      quote: input.quote?.trim() || undefined,
      source: input.source ?? existing.source,
      updatedAt: ts,
    };
    doc.notes = doc.notes.map((n) => (n.id === note.id ? note : n));
  } else {
    note = {
      id: randomUUID(),
      kind: input.kind,
      body,
      anchor: input.anchor?.trim() || undefined,
      quote: input.quote?.trim() || undefined,
      source: input.source,
      createdAt: ts,
      updatedAt: ts,
    };
    doc.notes.push(note);
  }
  doc.updatedAt = ts;
  writeChapter(doc);
  return { doc, note };
}

/** Remove a note by id. Returns the updated doc. */
export function deleteNote(
  slug: string,
  chapter: string,
  id: string,
): CompanionChapterDoc {
  const doc = readChapter(slug, chapter);
  const next = doc.notes.filter((n) => n.id !== id);
  doc.notes = next;
  doc.updatedAt = nowIso();
  return writeChapter(doc);
}

/** List every chapter that has at least one note, with counts (for the switcher). */
export function listChapters(slug: string): CompanionChapterSummary[] {
  const dir = companionDir(slug);
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const chapter = f.replace(/\.json$/, "");
      let count: number;
      try {
        const parsed = JSON.parse(
          readFileSync(join(dir, f), "utf8"),
        ) as CompanionChapterDoc;
        count = Array.isArray(parsed.notes) ? parsed.notes.length : 0;
      } catch {
        count = 0;
      }
      return { chapter, count };
    })
    .filter((c) => c.count > 0);
}
