/**
 * corpus-search.ts — GET /api/studio/corpus-search?q=<query>
 *
 * Read-only LIKE search over the `atoms` table (type='doctrine') in
 * content/knowledge-base/knowledge.db. Returns up to 10 matching atoms as
 * {id, snippet} pairs for the Key Focus cmdk command palette.
 *
 * Only doctrine atoms are returned — the Key Focus card is about editorial
 * focus, not metadata. The snippet is the first 220 chars of the body field.
 */
import type { APIRoute } from 'astro';
import Database from 'better-sqlite3';
import { join } from 'node:path';
import { apiOk, apiError, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

const DB_PATH = join(
  new URL('../../../../../content/knowledge-base/knowledge.db', import.meta.url).pathname,
);

const MAX_RESULTS = 10;
const SNIPPET_LEN = 220;

export const GET: APIRoute = ({ request }) => {
  const q = new URL(request.url).searchParams.get('q')?.trim() ?? '';
  if (!q || q.length < 2) return apiError('Query must be at least 2 characters', 400);
  if (q.length > 200) return apiError('Query too long', 400);

  try {
    const db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
    const rows = db
      .prepare(
        `SELECT id, substr(body, 1, ?) AS snippet
         FROM atoms
         WHERE type = 'doctrine'
           AND body LIKE '%' || ? || '%'
         ORDER BY confidence DESC, first_seen_date ASC
         LIMIT ?`,
      )
      .all(SNIPPET_LEN, q, MAX_RESULTS) as { id: string; snippet: string }[];
    db.close();
    return apiOk({ q, results: rows });
  } catch (e) {
    return apiServerError(`corpus search failed: ${String(e)}`);
  }
};
