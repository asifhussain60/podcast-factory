/**
 * GET /api/corpus/atoms
 *
 * Returns atoms from knowledge.db with optional filters and pagination.
 *
 * Query params:
 *   type          — atom type (quran, doctrine, term, hadith, etymology, poetry)
 *   tradition     — tradition filter (universal, fatimid-ismaili, ismaili)
 *   content_level — content_level filter (general, advanced, taveel, mamsool, mabda_maad, haqaiq)
 *   q             — body full-text LIKE filter
 *   page          — zero-based page index (default 0)
 *   pageSize      — atoms per page (default 500, max 2000)
 *   includeQuran  — 'true' to include the 6,236 Quran atoms (default false)
 *
 * Returns: { atoms, total, page, pageSize, facets }
 */

import type { APIRoute } from 'astro';
import { listAtoms } from '../../../lib/db/knowledge';

export const GET: APIRoute = ({ request }) => {
  try {
    const url = new URL(request.url);
    const p = url.searchParams;

    const pageSize = Math.min(2000, Math.max(1, Number(p.get('pageSize') ?? 500)));
    const page = Math.max(0, Number(p.get('page') ?? 0));

    const result = listAtoms({
      type: p.get('type') ?? undefined,
      tradition: p.get('tradition') ?? undefined,
      content_level: p.get('content_level') ?? undefined,
      q: p.get('q') ?? undefined,
      page,
      pageSize,
      includeQuran: p.get('includeQuran') === 'true',
    });

    return new Response(JSON.stringify({ ok: true, ...result }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(
      JSON.stringify({ ok: false, error: String(e) }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }
};
