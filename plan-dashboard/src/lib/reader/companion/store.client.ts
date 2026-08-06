/**
 * companion/store.client.ts — the client-side persistence seam.
 *
 * The panel talks ONLY to a CompanionStore, never to fetch() or a URL directly.
 * That indirection is the loose coupling: today the store is API-backed
 * (createApiStore), but a localStorage buffer, an in-memory mock for tests, or a
 * future sync backend can be dropped in without touching a single component.
 */
import { apiFetch } from "../../api-fetch";
import { safeChapterKey } from "./keys";
import type {
  CompanionChapterDoc,
  CompanionChapterSummary,
  CompanionNote,
  CompanionNoteInput,
} from "./types";

export interface CompanionStore {
  read(slug: string, chapter: string): Promise<CompanionChapterDoc>;
  listChapters(slug: string): Promise<CompanionChapterSummary[]>;
  upsert(
    slug: string,
    chapter: string,
    note: CompanionNoteInput,
  ): Promise<CompanionNote>;
  /** Re-point a note at the wording its passage now carries — quote only. */
  reanchor(
    slug: string,
    chapter: string,
    id: string,
    quote: string,
  ): Promise<CompanionNote>;
  /** Mark a machine-filed note as read and kept — `review` only. */
  accept(slug: string, chapter: string, id: string): Promise<CompanionNote>;
  remove(slug: string, chapter: string, id: string): Promise<void>;
}

const BASE = "/api/studio/companion-notes";

/** The default, API-backed store. */
export function createApiStore(): CompanionStore {
  return {
    async read(slug, chapter) {
      const key = safeChapterKey(chapter);
      return apiFetch<CompanionChapterDoc>(BASE, {
        query: { slug, chapter: key },
      });
    },
    async listChapters(slug) {
      const data = await apiFetch<{ chapters: CompanionChapterSummary[] }>(
        BASE,
        { query: { slug, list: 1 } },
      );
      return data.chapters;
    },
    async upsert(slug, chapter, note) {
      const key = safeChapterKey(chapter);
      return apiFetch<CompanionNote>(BASE, {
        method: "POST",
        body: { slug, chapter: key, note },
      });
    },
    async reanchor(slug, chapter, id, quote) {
      const key = safeChapterKey(chapter);
      return apiFetch<CompanionNote>(BASE, {
        method: "PATCH",
        body: { slug, chapter: key, id, quote },
      });
    },
    async accept(slug, chapter, id) {
      const key = safeChapterKey(chapter);
      return apiFetch<CompanionNote>(BASE, {
        method: "PATCH",
        body: { slug, chapter: key, id, review: "kept" },
      });
    },
    async remove(slug, chapter, id) {
      const key = safeChapterKey(chapter);
      await apiFetch<CompanionChapterDoc>(BASE, {
        method: "DELETE",
        query: { slug, chapter: key, id },
      });
    },
  };
}

/** Process-wide default so components can `import { defaultStore }` and go. */
export const defaultStore: CompanionStore = createApiStore();
