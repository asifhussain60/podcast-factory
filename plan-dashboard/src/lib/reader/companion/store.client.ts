/**
 * companion/store.client.ts — the client-side persistence seam.
 *
 * The panel talks ONLY to a CompanionStore, never to fetch() or a URL directly.
 * That indirection is the loose coupling: today the store is API-backed
 * (createApiStore), but a localStorage buffer, an in-memory mock for tests, or a
 * future sync backend can be dropped in without touching a single component.
 */
import { safeChapterKey } from './keys';
import type { CompanionChapterDoc, CompanionChapterSummary, CompanionNote, CompanionNoteInput } from './types';

export interface CompanionStore {
  read(slug: string, chapter: string): Promise<CompanionChapterDoc>;
  listChapters(slug: string): Promise<CompanionChapterSummary[]>;
  upsert(slug: string, chapter: string, note: CompanionNoteInput): Promise<CompanionNote>;
  remove(slug: string, chapter: string, id: string): Promise<void>;
}

interface Envelope<T> {
  ok: boolean;
  data?: T;
  error?: string;
}

async function json<T>(res: Response): Promise<T> {
  const env = (await res.json()) as Envelope<T>;
  if (!env.ok || env.data === undefined) throw new Error(env.error || `request failed (${res.status})`);
  return env.data;
}

const BASE = '/api/studio/companion-notes';

/** The default, API-backed store. */
export function createApiStore(): CompanionStore {
  return {
    async read(slug, chapter) {
      const key = safeChapterKey(chapter);
      return json<CompanionChapterDoc>(await fetch(`${BASE}?slug=${slug}&chapter=${key}`));
    },
    async listChapters(slug) {
      const data = await json<{ chapters: CompanionChapterSummary[] }>(
        await fetch(`${BASE}?slug=${slug}&list=1`),
      );
      return data.chapters;
    },
    async upsert(slug, chapter, note) {
      const key = safeChapterKey(chapter);
      return json<CompanionNote>(
        await fetch(BASE, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ slug, chapter: key, note }),
        }),
      );
    },
    async remove(slug, chapter, id) {
      const key = safeChapterKey(chapter);
      await json<CompanionChapterDoc>(
        await fetch(`${BASE}?slug=${slug}&chapter=${key}&id=${encodeURIComponent(id)}`, {
          method: 'DELETE',
        }),
      );
    },
  };
}

/** Process-wide default so components can `import { defaultStore }` and go. */
export const defaultStore: CompanionStore = createApiStore();
