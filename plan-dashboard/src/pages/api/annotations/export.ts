import type { APIRoute } from 'astro';
import { getChapterAnnotationSnapshot } from '../../../lib/db/annotations';
import { writeAnnotationExportFile, type QueueItem } from '../../../lib/reader/annotation-export';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  let body: {
    book: string;
    chapter: string;
    bookTitle?: string;
    queue: QueueItem[];
  };

  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400,
      headers: { 'content-type': 'application/json' },
    });
  }

  const { book, chapter, bookTitle, queue } = body;
  if (!book || !chapter || !Array.isArray(queue)) {
    return new Response(JSON.stringify({ error: 'Missing required fields' }), {
      status: 400,
      headers: { 'content-type': 'application/json' },
    });
  }

  try {
    const snapshot = getChapterAnnotationSnapshot(book, chapter);
    const annotations = snapshot.annotations.map((a) => ({
      para_idx: a.para_idx,
      tag_label: a.tag_label,
      tag_color: a.tag_color,
      tag_icon: a.tag_icon,
    }));
    const notes = snapshot.notes.map((n) => ({ para_idx: n.para_idx, note: n.note }));

    const { combinedText, relativePath } = await writeAnnotationExportFile({
      book,
      chapter,
      bookTitle,
      queue,
      annotations,
      notes,
    });

    return new Response(JSON.stringify({
      ok: true,
      combinedText,
      relativePath,
      itemCount: queue.length,
    }), {
      headers: { 'content-type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { 'content-type': 'application/json' },
    });
  }
};
