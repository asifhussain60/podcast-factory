/**
 * GET /api/wisdom/search?q=<keyword>&limit=<n>
 *
 * Wave J (J5): Wisdom topic keyword search via source_library_server.py.
 * Proxies to localhost:4390/topic/search.
 * Returns 503 when local server is unreachable.
 */

import type { APIRoute } from 'astro';

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const q = url.searchParams.get('q');
  if (!q || q.trim().length < 2) {
    return new Response(JSON.stringify({ error: 'q param required (min 2 chars)' }), { status: 400 });
  }
  const limit = Math.min(20, Math.max(1, Number(url.searchParams.get('limit') ?? '10')));

  // Reuse the localServerClient's raw fetch via a direct call
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 300);
    const res = await fetch(
      `http://localhost:4390/topic/search?q=${encodeURIComponent(q)}&limit=${limit}`,
      { signal: ctrl.signal },
    );
    clearTimeout(timer);
    if (!res.ok) {
      return new Response(JSON.stringify({ error: `server ${res.status}`, results: [] }), {
        status: 502, headers: { 'content-type': 'application/json' },
      });
    }
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=300' },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: 'local source library server unreachable', results: [] }),
      { status: 503, headers: { 'content-type': 'application/json' } },
    );
  }
};
