/**
 * chapters.ts — chapter + episode discovery for the library viewer.
 *
 * Ported from podcast-reader/src/lib/book-content.ts, adapted to call into
 * the canonical content-paths resolver (so it follows the same source of
 * truth the library index and the orchestrator use).
 */
import { readFile, readdir, stat } from "node:fs/promises";
import { join } from "node:path";
import { load as yamlLoad } from "js-yaml";

import { findContent } from "../content-paths";
import { simplifyTransliteration } from "../translit";

export interface BookChapter {
  slug: string; // 'ch01-the-perfect-and-the-perfection-of-the-soul'
  numericId: number | null;
  title: string;
  filePath: string;
  bytes: number;
}

export interface BookEpisode {
  slug: string;
  episodeNumber: number | null;
  title: string;
  sourceChapterRef: string | null;
  filePath: string;
  contractKeys: string[];
  // session grouping (chapter-density standard — absent on flat books)
  sessionIndex: number | null;
  sessionTitle: string | null;
  sessionEpisode: number | null;
}

export interface BookSession {
  index: number;
  title: string;
  slug: string;
  episodeNumbers: number[];
  episodeCount: number;
}

export interface BookIndex {
  book: string;
  rootPath: string;
  chapters: BookChapter[];
  episodes: BookEpisode[];
}

async function safeStat(p: string) {
  try {
    return await stat(p);
  } catch {
    return null;
  }
}

async function discoverChapters(root: string): Promise<BookChapter[]> {
  const dir = join(root, "chapters");
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }

  const out: BookChapter[] = [];
  for (const name of entries) {
    if (!name.endsWith(".txt") && !name.endsWith(".md")) continue;
    if (name.startsWith(".") || name.startsWith("_")) continue;
    const filePath = join(dir, name);
    const slug = name.replace(/\.(txt|md)$/i, "");
    const numMatch = slug.match(/^ch(\d+)/i);
    const numericId = numMatch ? Number(numMatch[1]) : null;

    let title = slug
      .replace(/^ch\d+-/i, "")
      .replace(/-/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    let bytes = 0;
    try {
      const buf = await readFile(filePath, "utf-8");
      bytes = buf.length;
      const m = buf.match(/^#\s+(.+)$/m);
      if (m) title = m[1].trim();
    } catch {
      /* noop */
    }
    out.push({
      slug,
      numericId,
      title: simplifyTransliteration(title),
      filePath,
      bytes,
    });
  }
  return out.sort((a, b) => (a.numericId ?? 999) - (b.numericId ?? 999));
}

async function discoverEpisodes(root: string): Promise<BookEpisode[]> {
  const dir = join(root, "chapter-contracts");
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }

  const out: BookEpisode[] = [];
  for (const name of entries) {
    if (!name.endsWith(".yml") && !name.endsWith(".yaml")) continue;
    if (name.startsWith(".") || name.startsWith("_")) continue;
    const filePath = join(dir, name);
    const slug = name.replace(/\.(yml|yaml)$/i, "");
    try {
      const raw = await readFile(filePath, "utf-8");
      const parsed = yamlLoad(raw) as Record<string, unknown> | null;
      if (!parsed || typeof parsed !== "object") {
        out.push({
          slug,
          episodeNumber: null,
          title: slug.replace(/-/g, " "),
          sourceChapterRef: null,
          filePath,
          contractKeys: [],
          sessionIndex: null,
          sessionTitle: null,
          sessionEpisode: null,
        });
        continue;
      }
      out.push({
        slug,
        episodeNumber:
          typeof parsed.episode_number === "number"
            ? parsed.episode_number
            : null,
        title:
          typeof parsed.title === "string"
            ? parsed.title
            : slug.replace(/-/g, " "),
        sourceChapterRef:
          typeof parsed.chapter_ref === "string"
            ? parsed.chapter_ref
            : typeof parsed.source_chapter_ref === "string" ||
                typeof parsed.source_chapter_ref === "number"
              ? String(parsed.source_chapter_ref)
              : null,
        filePath,
        contractKeys: Object.keys(parsed),
        sessionIndex:
          typeof parsed.session_index === "number"
            ? parsed.session_index
            : null,
        sessionTitle:
          typeof parsed.session_title === "string"
            ? parsed.session_title
            : null,
        sessionEpisode:
          typeof parsed.session_episode === "number"
            ? parsed.session_episode
            : null,
      });
    } catch {
      /* noop */
    }
  }
  return out.sort(
    (a, b) => (a.episodeNumber ?? 999) - (b.episodeNumber ?? 999),
  );
}

/**
 * Discover the book's Session grouping from its chapter contracts.
 * Returns [] for flat books (no session_* fields anywhere) — every consumer
 * is presence-gated and renders the flat layout in that case.
 */
export async function discoverSessions(root: string): Promise<BookSession[]> {
  const dir = join(root, "chapter-contracts");
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }

  const byIndex = new Map<number, BookSession>();
  for (const name of entries) {
    if (!name.endsWith(".yml") && !name.endsWith(".yaml")) continue;
    if (name.startsWith(".") || name.startsWith("_")) continue;
    try {
      const parsed = yamlLoad(
        await readFile(join(dir, name), "utf-8"),
      ) as Record<string, unknown> | null;
      if (!parsed || typeof parsed !== "object") continue;
      const idx =
        typeof parsed.session_index === "number" ? parsed.session_index : null;
      if (idx === null) continue;
      let session = byIndex.get(idx);
      if (!session) {
        session = {
          index: idx,
          title:
            typeof parsed.session_title === "string"
              ? parsed.session_title
              : `Session ${idx}`,
          slug:
            typeof parsed.session_slug === "string"
              ? parsed.session_slug
              : `session-${idx}`,
          episodeNumbers: [],
          episodeCount:
            typeof parsed.session_episode_count === "number"
              ? parsed.session_episode_count
              : 0,
        };
        byIndex.set(idx, session);
      }
      if (typeof parsed.episode_number === "number")
        session.episodeNumbers.push(parsed.episode_number);
    } catch {
      /* noop */
    }
  }
  const sessions = [...byIndex.values()].sort((a, b) => a.index - b.index);
  for (const s of sessions) s.episodeNumbers.sort((a, b) => a - b);
  return sessions;
}

export async function loadBookIndex(slug: string): Promise<BookIndex | null> {
  const ref = await findContent(slug);
  if (!ref) return null;
  const s = await safeStat(ref.dir);
  if (!s?.isDirectory()) return null;

  const [chapters, episodes] = await Promise.all([
    discoverChapters(ref.dir),
    discoverEpisodes(ref.dir),
  ]);
  return { book: slug, rootPath: ref.dir, chapters, episodes };
}

export async function loadChapterSource(filePath: string): Promise<string> {
  return readFile(filePath, "utf-8");
}
