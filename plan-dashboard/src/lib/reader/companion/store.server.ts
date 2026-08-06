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

/** Trimmed, empties dropped. `undefined` when nothing survives, so a note with no
 *  etymology has no key rather than an empty array. */
function cleanItems(items: string[] | undefined): string[] | undefined {
  if (!Array.isArray(items)) return undefined;
  const out = items.map((s) => String(s ?? "").trim()).filter(Boolean);
  return out.length ? out : undefined;
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
      // ABSENT means KEEP, unlike `anchor` directly above (Asif, 2026-08-02).
      // The two are not symmetrical and deliberately so: a card's title is the
      // author's to write and to clear, so an absent anchor is an instruction.
      // The quote is not authorable anywhere in the UI — it is where the note
      // LIVES in the chapter — so an absent quote can only mean the caller had
      // nothing to say about the anchoring, and honouring that as "clear it"
      // let a card save from a panel holding a pre-edit copy silently undo a
      // re-anchor. Clearing a quote is `reanchorNote(..., "")`, said out loud.
      quote:
        input.quote === undefined
          ? existing.quote
          : input.quote.trim() || undefined,
      etymology:
        input.etymology === undefined
          ? existing.etymology
          : cleanItems(input.etymology),
      source: input.source ?? existing.source,
      review: input.review ?? existing.review,
      updatedAt: ts,
    };
    doc.notes = doc.notes.map((n) => (n.id === note.id ? note : n));
  } else {
    note = {
      // A caller-supplied id is HONOURED on create. The student-reader pass
      // derives each note's id from the chapter and the sentence it anchors to,
      // which is the whole of "deterministic, not random" (Asif, 2026-08-06):
      // a second run over unchanged prose must UPDATE the note it wrote last
      // time, not file a duplicate beside it. Minting a fresh uuid here would
      // have made re-running the pass additive forever. A human's own note
      // sends no id and still gets one.
      id: input.id || randomUUID(),
      kind: input.kind,
      body,
      anchor: input.anchor?.trim() || undefined,
      quote: input.quote?.trim() || undefined,
      etymology: cleanItems(input.etymology),
      source: input.source,
      review: input.review,
      createdAt: ts,
      updatedAt: ts,
    };
    doc.notes.push(note);
  }
  doc.updatedAt = ts;
  writeChapter(doc);
  return { doc, note };
}

/**
 * Re-point one note at the wording its passage now carries.
 *
 * The narrowest possible write: `quote` and `updatedAt`, nothing else. The
 * Composer calls this after saving a chapter in which an explained sentence was
 * edited, so the note keeps pointing at the sentence rather than at the wording
 * that sentence used to have. Going through `upsertNote` instead would mean
 * sending a whole note back to say one field changed, and every field not sent
 * is a field at risk — which is the bug this exists to avoid, not repeat.
 *
 * Returns null when the id is unknown: a stale client re-anchoring a note that
 * was deleted elsewhere must not resurrect it.
 */
export function reanchorNote(
  slug: string,
  chapter: string,
  id: string,
  quote: string,
): CompanionNote | null {
  const doc = readChapter(slug, chapter);
  const existing = doc.notes.find((n) => n.id === id);
  if (!existing) return null;
  const next: CompanionNote = {
    ...existing,
    quote: quote.trim() || undefined,
    updatedAt: nowIso(),
  };
  doc.notes = doc.notes.map((n) => (n.id === id ? next : n));
  doc.updatedAt = next.updatedAt;
  writeChapter(doc);
  return next;
}

/**
 * Mark one note as read and kept.
 *
 * As narrow as `reanchorNote` above and for the same reason: `review` and
 * `updatedAt`, nothing else. Accepting is a judgement about a note, not an edit
 * of it, so it must not travel as a whole-note save — every field sent is a
 * field at risk, and the panel may be holding a copy from before an edit.
 *
 * Returns null on an unknown id: accepting a note deleted elsewhere must not
 * resurrect it.
 */
export function acceptNote(
  slug: string,
  chapter: string,
  id: string,
): CompanionNote | null {
  const doc = readChapter(slug, chapter);
  const existing = doc.notes.find((n) => n.id === id);
  if (!existing) return null;
  const next: CompanionNote = {
    ...existing,
    review: "kept",
    updatedAt: nowIso(),
  };
  doc.notes = doc.notes.map((n) => (n.id === id ? next : n));
  doc.updatedAt = next.updatedAt;
  writeChapter(doc);
  return next;
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
