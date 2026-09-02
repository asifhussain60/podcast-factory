/**
 * catalog-cards.server.ts — the counts behind the library grid.
 *
 * Split out of `catalog.server.ts` on 2026-09-02, when that file crossed the
 * 850-line ceiling `npm run ratchets` holds new files to. A real seam rather
 * than a cut made to fit: everything left there answers "what is IN this book" —
 * its chapters, its episodes, its decks, one row of media — and everything here
 * answers a different question, "what does the SHELF need to draw a card for
 * each of these slugs". The two are read by different surfaces and neither
 * calls the other.
 *
 * Re-exported from `catalog.server` so no caller moved: six modules and two test
 * files name `LibraryCard` and `libraryCards` at that path, and a split that
 * makes six files change import lines is a split that gets reverted.
 */
import type { D1Database } from "@cloudflare/workers-types";

import { servable } from "~/server/catalog-sql.server";

export interface LibraryCard {
  chapters: number;
  firstChapterKey: string | null;
  /**
   * Raw words, NOT minutes.
   *
   * This used to be a precomputed `minutes`, which made the card the only place
   * in the app where reading time was worked out server-side — with a different
   * zero rule from the book page's client-side one, so the same book could show
   * no pill here and "1 min read" there. `app/lib/facts.ts` now does the sum for
   * both, once.
   */
  words: number;
  episodes: number;
  recorded: number;
  /** A print edition exists at all. */
  hasPdf: boolean;
  /** ...and is in R2, so the download works. Kept apart: see `describeContents`. */
  pdfAvailable: boolean;
  deckPages: number;
  /** At least one deck page is in R2. */
  deckAvailable: boolean;
  titleOriginal: string | null;
  titleLanguage: "ar" | "ur" | "zh" | null;
  /**
   * Who wrote it. NEVER null — the column is NOT NULL with an 'Anonymous'
   * default, so a card can print a credit unconditionally the way a jacket
   * does, instead of the template carrying a rule about missing names.
   *
   * `?? "Anonymous"` below is for the LEFT JOIN, not for the column: a
   * `content_unit` row with no `unit_detail` yet yields SQL NULL for every `d.`
   * field regardless of that column's default.
   */
  author: string;
  /** The one-line form the card actually prints — see migration 0021. */
  authorShort: string;
  /** The library ribbon's category — null on a book not yet classified. */
  studyTrack: string | null;
}

export interface CardPlayableEpisode {
  slug: string;
  number: number;
  title: string;
  audioKey: string;
  durationS: number | null;
  transcriptKey: string | null;
  /**
   * The chapter this recording IS, when one exists — the same join
   * `episodesAreChapterNarration` uses, so the card's play button and the
   * book page's own tab agree about which books this is true for. Null sends
   * the button to `?tab=listen`, exactly as it always has.
   */
  chapterKey: string | null;
}

/**
 * Counts for the library grid, for a list of slugs the caller has ALREADY
 * resolved through `visibleUnits`.
 *
 * The slugs are bound, not interpolated, and the query is scoped to exactly the
 * ones passed. Counting every unit and filtering in JavaScript would be simpler
 * and would leak the shape of books the viewer cannot see — how many chapters,
 * how many recordings — to anyone who reads a network response.
 */
export async function libraryCards(
  db: D1Database,
  slugs: string[],
): Promise<Map<string, LibraryCard>> {
  const cards = new Map<string, LibraryCard>();
  if (slugs.length === 0) return cards;

  const placeholders = slugs.map((_, i) => `?${i + 1}`).join(", ");

  const { results } = await db
    .prepare(
      `SELECT u.slug,
              d.author,
              d.author_short,
              d.title_arabic,
              d.title_language,
              d.study_track,
              -- TWO facts, deliberately not collapsed: the print edition exists,
              -- and it is in R2 so the link works. This used to be one column
              -- (pdf_ready, uploaded only), which meant the card could not say
              -- "not uploaded yet" the way the book page does — it either
              -- promised a download or said nothing. Both are now carried and
              -- describeContents decides the wording for both surfaces.
              (SELECT count(*) FROM media_asset m WHERE m.key = d.pdf_key) AS pdf_exists,
              (SELECT count(*) FROM media_asset m
                WHERE m.key = d.pdf_key AND ${servable("m.uploaded_at")}) AS pdf_ready,
              (SELECT count(*)          FROM chapter c WHERE c.slug = u.slug) AS chapters,
              (SELECT c.anchor_key       FROM chapter c
                WHERE c.slug = u.slug ORDER BY c.idx LIMIT 1) AS first_chapter_key,
              (SELECT coalesce(sum(c.word_count), 0) FROM chapter c WHERE c.slug = u.slug) AS words,
              (SELECT count(*)          FROM episode e WHERE e.slug = u.slug) AS episodes,
              (SELECT count(*)          FROM episode e
                 JOIN media_asset m ON m.key = e.audio_key
                WHERE e.slug = u.slug AND ${servable("m.uploaded_at")}) AS recorded,
              (SELECT count(*)          FROM media_asset m
                WHERE m.slug = u.slug AND m.kind = 'deck-page') AS deck_pages,
              (SELECT count(*)          FROM media_asset m
                WHERE m.slug = u.slug AND m.kind = 'deck-page'
                  AND ${servable("m.uploaded_at")}) AS deck_ready
       FROM content_unit u
       LEFT JOIN unit_detail d ON d.slug = u.slug
       WHERE u.slug IN (${placeholders})`,
    )
    .bind(...slugs)
    .all<{
      slug: string;
      author: string | null;
      author_short: string | null;
      title_arabic: string | null;
      title_language: "ar" | "ur" | "zh" | null;
      study_track: string | null;
      pdf_exists: number;
      pdf_ready: number;
      chapters: number;
      first_chapter_key: string | null;
      words: number;
      episodes: number;
      recorded: number;
      deck_pages: number;
      deck_ready: number;
    }>();

  for (const r of results) {
    cards.set(r.slug, {
      chapters: r.chapters,
      firstChapterKey: r.first_chapter_key,
      words: r.words,
      episodes: r.episodes,
      recorded: r.recorded,
      hasPdf: r.pdf_exists > 0,
      pdfAvailable: r.pdf_ready > 0,
      deckPages: r.deck_pages,
      deckAvailable: r.deck_ready > 0,
      author: r.author ?? "Anonymous",
      authorShort: r.author_short ?? r.author ?? "Anonymous",
      titleOriginal: r.title_arabic,
      titleLanguage:
        r.title_arabic === null ? null : (r.title_language ?? "ar"),
      studyTrack: r.study_track,
    });
  }

  return cards;
}

/**
 * The playable episode rows a library card can start.
 *
 * The caller passes slugs already filtered through access. This returns only
 * uploaded audio, matching the book page's Listen tab, so a card never offers a
 * play button that opens onto a 404.
 */
export async function playableEpisodesForCards(
  db: D1Database,
  slugs: string[],
): Promise<Map<string, CardPlayableEpisode[]>> {
  const episodes = new Map<string, CardPlayableEpisode[]>();
  if (slugs.length === 0) return episodes;

  const placeholders = slugs.map((_, i) => `?${i + 1}`).join(", ");

  const { results } = await db
    .prepare(
      `SELECT e.slug, e.number, e.title, e.audio_key, e.duration_s,
              CASE
                WHEN e.transcript_key IS NOT NULL AND ${servable("transcript.uploaded_at")}
                THEN e.transcript_key
                ELSE NULL
              END AS transcript_key,
              chapter.anchor_key AS chapter_key
         FROM episode e
         JOIN media_asset audio
           ON audio.key = e.audio_key
          AND ${servable("audio.uploaded_at")}
         LEFT JOIN media_asset transcript
           ON transcript.key = e.transcript_key
         LEFT JOIN episode_chapter ec
           ON ec.slug = e.slug AND ec.number = e.number
         LEFT JOIN chapter_narration chapter
           ON chapter.slug = e.slug
          AND chapter.anchor_key = ec.anchor_key
          AND chapter.audio_key = e.audio_key
        WHERE e.slug IN (${placeholders})
        ORDER BY e.slug, e.number`,
    )
    .bind(...slugs)
    .all<{
      slug: string;
      number: number;
      title: string;
      audio_key: string;
      duration_s: number | null;
      transcript_key: string | null;
      chapter_key: string | null;
    }>();

  for (const r of results) {
    const slot = episodes.get(r.slug) ?? [];
    slot.push({
      slug: r.slug,
      number: r.number,
      title: r.title,
      audioKey: r.audio_key,
      durationS: r.duration_s,
      transcriptKey: r.transcript_key,
      chapterKey: r.chapter_key,
    });
    episodes.set(r.slug, slot);
  }

  return episodes;
}
