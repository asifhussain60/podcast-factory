import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { contentDir, findContent, getRepoRoot } from '../content-paths';

export interface QueueItem {
  id: string;
  kind: 'action' | 'marker';
  scope: 'paragraph' | 'book' | 'global';
  paraIdx: number | null;
  paragraphPreview: string;
  actionType: string;
  instruction: string;
  tags: string[];
  createdAt: string;
}

export interface AnnotationExportPayload {
  book: string;
  chapter: string;
  bookTitle?: string;
  queue: QueueItem[];
  annotations: Array<{
    para_idx: number;
    tag_label: string;
    tag_color: string;
    tag_icon: string;
  }>;
  notes: Array<{ para_idx: number; note: string }>;
}

function buildCombinedInstructionText(payload: AnnotationExportPayload): string {
  const lines: string[] = [];
  lines.push(`# Annotation instruction set for ${payload.book} / ${payload.chapter}`);
  lines.push('');
  lines.push('## Classification markers');
  if (payload.annotations.length === 0) {
    lines.push('- none');
  } else {
    for (const a of payload.annotations) {
      lines.push(`- paragraph ${a.para_idx}: ${a.tag_label}`);
    }
  }

  lines.push('');
  lines.push('## Editorial notes');
  if (payload.notes.length === 0) {
    lines.push('- none');
  } else {
    for (const n of payload.notes) {
      lines.push(`- paragraph ${n.para_idx}: ${n.note}`);
    }
  }

  lines.push('');
  lines.push('## Action queue');
  if (payload.queue.length === 0) {
    lines.push('- none');
  } else {
    payload.queue.forEach((q, i) => {
      lines.push(`${i + 1}. [${q.scope}] ${q.actionType}`);
      if (q.paraIdx !== null) lines.push(`   paragraph: ${q.paraIdx}`);
      if (q.tags.length) lines.push(`   tags: ${q.tags.join(', ')}`);
      if (q.paragraphPreview) lines.push(`   text: ${q.paragraphPreview}`);
      lines.push(`   instruction: ${q.instruction}`);
    });
  }

  lines.push('');
  lines.push('## Execution request');
  lines.push('Apply these queued actions in order. Preserve voice and factual integrity, and report what changed for each item.');

  return lines.join('\n');
}

export async function writeAnnotationExportFile(payload: AnnotationExportPayload): Promise<{
  combinedText: string;
  relativePath: string;
}> {
  const ref = await findContent(payload.book);
  const category = ref?.category ?? 'books';
  const draftRoot = contentDir(payload.book, 'drafts', category);
  const dir = path.join(draftRoot, '_system', 'annotation-intelligence');
  const filePath = path.join(dir, `${payload.chapter}.json`);
  const relativePath = path.relative(getRepoRoot(), filePath);

  const combinedText = buildCombinedInstructionText(payload);

  const doc = {
    schema: 'annotation-intelligence-v1',
    updated_at: new Date().toISOString(),
    book: payload.book,
    chapter: payload.chapter,
    book_title: payload.bookTitle ?? payload.book,
    queue: payload.queue,
    annotations: payload.annotations,
    notes: payload.notes,
    combined_instruction_text: combinedText,
  };

  await mkdir(dir, { recursive: true });
  await writeFile(filePath, JSON.stringify(doc, null, 2) + '\n', 'utf-8');

  return { combinedText, relativePath };
}
