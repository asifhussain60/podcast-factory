/**
 * The shape of the Book Composer's server-rendered data island.
 *
 * Split out of book-composer.ts on 2026-08-16, when that file passed its size
 * ratchet. Types only — no behaviour — so this module compiles away entirely and
 * the split costs nothing at runtime.
 *
 * Several of these are the CLIENT half of a contract whose other half is written
 * in Astro (`ComposerView` in lib/reader/composer.ts). Their comments say which,
 * and those notes travelled with the types deliberately: a field's mirror is the
 * thing a reader most needs to know before changing it.
 */

import type { GlossaryEntry } from "../components/studio/editor/studio-editor-constants";
import type { PodcastChapterMeta } from "./compose-lane";

export type Align = "left" | "center" | "right";
export type Flow = "wrap" | "standalone";
export type PageFit = "avoid" | "before" | "isolate-plate";

export interface Visual {
  id: string;
  type: string;
  caption: string;
  file: string;
  src: string;
  suggested_anchor: string;
  chapter: string;
  cleaned: boolean;
  embedded_title: string;
}
export interface Citation {
  ar: string;
  tr: string;
}
export interface Chapter {
  anchor: string;
  key: string;
  title: string;
  paras: number;
  /** A stable name per prose paragraph, in order — the key the Arabic-source
   *  alignment is stored under. Mirrors ComposerChapter.paraKeys in
   *  lib/reader/composer.ts, computed there by the shared block splitter. */
  paraKeys: string[];
  citations: Citation[];
  /** TipTap-safe seed for edit mode. Mirrors ComposerChapter.editHtml in
   *  lib/reader/composer.ts — see the bodyByKey note in boot(). */
  editHtml: string;
}
export interface Placement {
  visual_id: string;
  anchor: string;
  anchor_para: number | null;
  align: Align;
  flow: Flow;
  width_pct: number;
  caption: string;
  page_fit: PageFit;
}
export interface ComposerData {
  slug: string;
  chapters: Chapter[];
  visuals: Visual[];
  placements: Placement[];
  glossary: GlossaryEntry[];
  glossaryAll: GlossaryEntry[];
  /** RCA-001 AI-3 — chapterKey -> why a save would freeze machine text.
   *  Mirrors ComposerView.articulationWarnings in lib/reader/composer.ts. */
  articulationWarnings?: Record<string, string>;
  /** The read-only Podcast lane's chapter list (metadata only). Mirrors
   *  ComposerView.podcastChapters; absent for a book with no podcast source. */
  podcastChapters?: PodcastChapterMeta[];
  /** Gates the "Paste & Fix Chapter" action. Mirrors ComposerView.sessionsLane. */
  sessionsLane?: boolean;
}
