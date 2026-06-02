/**
 * GET /api/quran/etymology?root=<str>
 *
 * Wave J (J2): Arabic root etymology lookup from the KQUR Roots + Derivatives
 * mirror via source_library_server.py at localhost:4390.
 *
 * Returns: { found, term, arabic, root, grammar_tag, definition, etymology, related }
 * Returns 503 when local server is unreachable (no external fallback — etymology
 * data only exists in the local mirror).
 */

import type { APIRoute } from 'astro';
import { fetchLocalEtymology } from '../../../lib/localServerClient';

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const root = url.searchParams.get('root') ?? url.searchParams.get('term');
  if (!root) {
    return new Response(JSON.stringify({ error: 'missing root or term param' }), { status: 400 });
  }

  const data = await fetchLocalEtymology(root);
  if (!data) {
    return new Response(
      JSON.stringify({ error: 'local source library server unreachable', found: false }),
      { status: 503, headers: { 'content-type': 'application/json' } },
    );
  }

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=3600' },
  });
};
