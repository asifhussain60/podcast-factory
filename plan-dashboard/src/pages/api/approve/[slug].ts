/**
 * Approve book API endpoint — Wave I (I4 / I5)
 * POST /api/approve/[slug]
 *
 * Sets approved=true + approved_at timestamp on the book's review-gate.json.
 * Same logic as approve_book.py — this is the UI-facing counterpart.
 */
import type { APIRoute } from 'astro';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

export const POST: APIRoute = async ({ params }) => {
  const { slug } = params;

  if (!slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
    return new Response(JSON.stringify({ error: 'Invalid slug' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const REPO_ROOT = join(new URL(import.meta.url).pathname, '../../../../../');
  const gatePath = join(REPO_ROOT, 'CONTENT', 'drafts', 'books', slug, '_system', 'review-gate.json');

  if (!existsSync(gatePath)) {
    return new Response(
      JSON.stringify({ error: `No review-gate.json found for "${slug}". Run Phase 06a first.` }),
      { status: 404, headers: { 'Content-Type': 'application/json' } },
    );
  }

  let gate: any;
  try {
    gate = JSON.parse(readFileSync(gatePath, 'utf-8'));
  } catch (e: any) {
    return new Response(
      JSON.stringify({ error: `Failed to read review-gate.json: ${e.message}` }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }

  if (gate.approved) {
    return new Response(
      JSON.stringify({ approved: true, approved_at: gate.approved_at, already: true }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  }

  const now = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  gate.approved = true;
  gate.approved_at = now;

  try {
    writeFileSync(gatePath, JSON.stringify(gate, null, 2), 'utf-8');
  } catch (e: any) {
    return new Response(
      JSON.stringify({ error: `Failed to write review-gate.json: ${e.message}` }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }

  return new Response(
    JSON.stringify({ approved: true, approved_at: now, slug }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
};
