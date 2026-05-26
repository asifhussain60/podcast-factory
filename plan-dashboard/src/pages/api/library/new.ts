import type { APIRoute } from 'astro';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import {
  ACTIVE_CATEGORIES,
  contentDir,
  findContent,
  type Category,
} from '../../../lib/content-paths';

export const prerender = false;

function isValidSlug(s: string): boolean {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(s);
}

function isValidCategory(c: string): c is Category {
  return (ACTIVE_CATEGORIES as readonly string[]).includes(c);
}

export const POST: APIRoute = async ({ request, redirect }) => {
  const form = await request.formData();
  const slug = String(form.get('slug') ?? '').trim();
  const category = String(form.get('category') ?? '').trim();
  const title = String(form.get('title') ?? '').trim();

  if (!isValidSlug(slug)) {
    return new Response(`invalid slug: must be kebab-case (lowercase a-z, 0-9, hyphens). Got ${JSON.stringify(slug)}`, { status: 400 });
  }
  if (!isValidCategory(category)) {
    return new Response(`invalid category: must be one of ${ACTIVE_CATEGORIES.join(', ')}`, { status: 400 });
  }

  // Refuse if slug already exists anywhere
  const existing = await findContent(slug);
  if (existing) {
    return new Response(`a piece of content with slug ${slug} already exists at ${existing.dir}`, { status: 409 });
  }

  const dir = contentDir(slug, 'drafts', category);
  await mkdir(dir, { recursive: true });
  await mkdir(join(dir, '_system'), { recursive: true });
  await mkdir(join(dir, '_system', 'source'), { recursive: true });
  await mkdir(join(dir, '_system', 'source', 'text'), { recursive: true });

  const metaLines = [
    `slug: ${slug}`,
    `category: ${category}`,
    `title: ${title || slug}`,
    `created: ${new Date().toISOString()}`,
    `stage: drafts`,
  ];
  await writeFile(join(dir, 'meta.yml'), metaLines.join('\n') + '\n', 'utf-8');

  return redirect(`/library/${slug}`, 303);
};
