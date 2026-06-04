import type { APIRoute } from 'astro';
import { mkdir, rename } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { archiveRoot, findContent } from '../../../../lib/content-paths';

export const prerender = false;

function todayStamp(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export const POST: APIRoute = async ({ params, redirect }) => {
  const slug = params.slug;
  if (!slug) return new Response('missing slug', { status: 400 });

  const ref = await findContent(slug);
  if (!ref) return new Response('content not found', { status: 404 });

  const dest = join(archiveRoot(), todayStamp(), ref.category, ref.slug);
  await mkdir(dirname(dest), { recursive: true });
  await rename(ref.dir, dest);

  return redirect('/library', 303);
};
