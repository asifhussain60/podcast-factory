/**
 * Discover books under ~/PROJECTS/podcast-factory/content/drafts/.
 *
 * History note: this file was originally named worktree-glob.ts when the
 * repo used the Option 2 container layout (podcast-factory/worktrees/<branch>/).
 * That layout was retired 2026-05-23 in favor of a single flat repo where
 * books live at content/drafts/<slug>/. The Worktree interface name is kept
 * for backward compatibility with downstream callers; treat the single
 * synthetic "worktree" as a stand-in for the develop branch.
 *
 * Resolvable via PODCAST_FACTORY_ROOT env var, defaulting to ~/PROJECTS/podcast-factory.
 */

import { readdir, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';

const DEFAULT_REPO_ROOT = join(homedir(), 'PROJECTS', 'podcast-factory');
const SYNTHETIC_WORKTREE_NAME = 'develop';  // single source — no more multi-branch worktrees

export interface Worktree {
  name: string;          // always 'develop' now — kept for backward compat
  path: string;          // absolute path to the repo root
  books: string[];       // book slugs found under content/drafts/
}

export function getRepoRoot(): string {
  return process.env.PODCAST_FACTORY_ROOT ?? DEFAULT_REPO_ROOT;
}

/** @deprecated Use getRepoRoot() — kept for any existing callers. */
export function getWorktreesRoot(): string {
  return getRepoRoot();
}

export function getPilotBook(): string {
  // v1 pilot scope is reopened: surface all books, not just kitab-al-riyad.
  // Callers that still respect this constant get the same behavior; new
  // callers should iterate Worktree.books instead.
  return 'kitab-al-riyad';
}

export async function discoverWorktrees(): Promise<Worktree[]> {
  // Lazy import to break the cycle (content-paths imports from this file).
  const { listContent } = await import('./content-paths');
  const repoRoot = getRepoRoot();
  const refs = await listContent({ stage: 'drafts', category: 'books' });
  return [{
    name: SYNTHETIC_WORKTREE_NAME,
    path: repoRoot,
    books: refs.map((r) => r.slug).sort(),
  }];
}
