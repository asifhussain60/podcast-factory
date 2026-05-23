/**
 * Discover worktrees and their books under ~/PROJECTS/podcast-factory/worktrees/.
 * v1 pilot scope: only books named `kitab-al-riyad` are surfaced as reachable;
 * other books are listed in the count but no routes are generated yet.
 *
 * The worktree root is resolvable via the PODCAST_FACTORY_ROOT env var, falling
 * back to the canonical path. This keeps the reader portable across machines
 * where the path convention may differ.
 */

import { readdir, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';

const DEFAULT_ROOT = join(homedir(), 'PROJECTS', 'podcast-factory', 'worktrees');
const PILOT_BOOK = 'kitab-al-riyad';

export interface Worktree {
  name: string;          // 'book-kar', 'book-asaas', etc.
  path: string;          // absolute path to the worktree
  books: string[];       // book slugs found under content/podcast/library/books/
}

export function getWorktreesRoot(): string {
  return process.env.PODCAST_FACTORY_ROOT ?? DEFAULT_ROOT;
}

export function getPilotBook(): string {
  return PILOT_BOOK;
}

export async function discoverWorktrees(): Promise<Worktree[]> {
  const root = getWorktreesRoot();
  let entries: string[];
  try {
    entries = await readdir(root);
  } catch {
    return [];
  }

  const worktrees: Worktree[] = [];
  for (const name of entries) {
    if (name.startsWith('.')) continue;
    const path = join(root, name);
    try {
      const s = await stat(path);
      if (!s.isDirectory()) continue;
    } catch {
      continue;
    }

    const booksRoot = join(path, 'content', 'podcast', 'library', 'books');
    let books: string[] = [];
    try {
      const bookEntries = await readdir(booksRoot);
      for (const b of bookEntries) {
        if (b.startsWith('.') || b.startsWith('_')) continue;
        try {
          const bs = await stat(join(booksRoot, b));
          if (bs.isDirectory()) books.push(b);
        } catch {
          // ignore
        }
      }
    } catch {
      // no books dir in this worktree — skip silently
    }

    worktrees.push({ name, path, books: books.sort() });
  }

  return worktrees.sort((a, b) => a.name.localeCompare(b.name));
}
