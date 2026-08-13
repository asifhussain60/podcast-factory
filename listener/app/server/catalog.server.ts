/**
 * What a unit CONTAINS: chapters, episodes, media.
 *
 * Deliberately separate from access.server.ts, which decides who may see what.
 * Nothing in this file asks that question or is capable of answering it — every
 * caller has already been through `requireUnitAccess`, and the one place a media
 * key is turned back into a permission check goes through `canRead` over there.
 * Keeping the entitlement rule in exactly one module is what makes it auditable.
 */

import { readingMinutes } from "~/lib/reading";

export interface ChapterSummary {
  anchorKey: string;
  idx: number;
  title: string;
  wordCount: number;
}

export interface ChapterNarrationCue {
  idx: number;
  blockIndex?: number;
  startS: number;
  endS: number;
  text: string;
}

export interface ChapterNarration {
  audioKey: string;
  durationS: number | null;
  cues: ChapterNarrationCue[];
}

export interface Chapter extends ChapterSummary {
  html: string;
  narration: ChapterNarration | null;
}

export interface Episode {
  number: number;
  title: string;
  blurb: string | null;
  style: string | null;
  /** NULL until the recording exists AND has been uploaded. See `hasAudio`. */
  audioKey: string | null;
  durationS: number | null;
  /** False while the file exists on disk but is not in R2 yet. */
  hasAudio: boolean;
  /**
   * The WebVTT of what is said, or null.
   *
   * Null carries TWO cases deliberately merged: no transcript was ever made, and
   * one was made but is not in R2 yet. The reader can do nothing with either, and
   * the only honest thing to render is the same absence — so the distinction is
   * kept out of the UI rather than surfaced as two shades of missing. It survives
   * where it matters, in `media_asset.uploaded_at`, which is what the publisher
   * and the uploader read.
   */
  transcriptKey: string | null;
  /** Chapters this episode covers — empty unless a human recorded the mapping. */
  chapters: string[];
  /** null when this book's episodes were never grouped, which is most books. */
  sessionNumber: number | null;
}

/** A named run of episodes. Called `book_session` in SQL — Better Auth owns `session`. */
export interface Session {
  number: number;
  title: string;
  episodes: Episode[];
}

export interface UnitDetail {
  titleArabic: string | null;
  /** Rendered at publish time by the same function as the chapters. */
  blurbHtml: string | null;
  editionNote: string | null;
  coverKey: string | null;
  pdfKey: string | null;
  pdfBytes: number | null;
  /** False while the file exists on disk but is not in R2. Never link to it. */
  pdfAvailable: boolean;
  publishedAt: string;
}

export interface DeckPage {
  key: string;
  available: boolean;
}

/** One slide deck: the pages, and what the author called it. */
export interface Deck {
  /** The folder it came from — 'ch01', or 'book' for a book-wide deck. "" for rows predating migration 0010. */
  id: string;
  /** Null for a book-wide deck, which needs no name because it is the only one. */
  title: string | null;
  pages: DeckPage[];
}

/** What else a book offers, for a surface that is already inside one of them. */
export interface Surfaces {
  /** Episodes with a recording actually in R2. Zero for most of the library. */
  episodes: number;
  /** Deck pages actually in R2. */
  deckPages: number;
  /** The print edition's key, or null unless the file is in R2. */
  pdfKey: string | null;
}

/**
 * The other ways this book can be taken — ONE query, for the reading page.
 *
 * The book page answers the same question with `sessionsOf` + `deckPagesOf` +
 * `detailOf`, because it needs every episode, every page and the whole detail
 * row to render them. The reader needs only whether each exists, and it asks on
 * every chapter, so it gets counts in a single round trip rather than three
 * result sets it would immediately throw away.
 *
 * "Exists" means IN R2, not on disk, in all three cases — a chip offering a
 * podcast that is not there yet is worse than no chip, and it is the same rule
 * the book page's tabs already apply.
 */
export async function surfacesOf(db: D1Database, slug: string): Promise<Surfaces> {
  const row = await db
    .prepare(
      `SELECT
         (SELECT count(*) FROM episode e
             JOIN media_asset m ON m.key = e.audio_key
            WHERE e.slug = ?1 AND m.uploaded_at IS NOT NULL) AS episodes,
         (SELECT count(*) FROM media_asset
            WHERE slug = ?1 AND kind = 'deck-page' AND uploaded_at IS NOT NULL) AS deck_pages,
         (SELECT d.pdf_key FROM unit_detail d
             JOIN media_asset m ON m.key = d.pdf_key
            WHERE d.slug = ?1 AND m.uploaded_at IS NOT NULL) AS pdf_key`,
    )
    .bind(slug)
    .first<{ episodes: number; deck_pages: number; pdf_key: string | null }>();

  return {
    episodes: row?.episodes ?? 0,
    deckPages: row?.deck_pages ?? 0,
    pdfKey: row?.pdf_key ?? null,
  };
}

export async function detailOf(db: D1Database, slug: string): Promise<UnitDetail | null> {
  const row = await db
    .prepare(
      `SELECT d.title_arabic, d.blurb_html, d.edition_note, d.cover_key, d.pdf_key, d.published_at,
              (SELECT m.bytes       FROM media_asset m WHERE m.key = d.pdf_key) AS pdf_bytes,
              (SELECT m.uploaded_at FROM media_asset m WHERE m.key = d.pdf_key) AS pdf_uploaded_at
       FROM unit_detail d WHERE d.slug = ? LIMIT 1`,
    )
    .bind(slug)
    .first<{
      title_arabic: string | null;
      blurb_html: string | null;
      edition_note: string | null;
      cover_key: string | null;
      pdf_key: string | null;
      published_at: string;
      pdf_bytes: number | null;
      pdf_uploaded_at: string | null;
    }>();

  if (row === null) return null;

  return {
    titleArabic: row.title_arabic,
    blurbHtml: row.blurb_html,
    editionNote: row.edition_note,
    coverKey: row.cover_key,
    pdfKey: row.pdf_key,
    pdfBytes: row.pdf_bytes,
    pdfAvailable: row.pdf_uploaded_at !== null,
    publishedAt: row.published_at,
  };
}

/** The table of contents. Never carries `html` — a book's prose is megabytes. */
export async function chaptersOf(db: D1Database, slug: string): Promise<ChapterSummary[]> {
  const { results } = await db
    .prepare(
      `SELECT anchor_key, idx, title, word_count FROM chapter
       WHERE slug = ? ORDER BY idx`,
    )
    .bind(slug)
    .all<{ anchor_key: string; idx: number; title: string; word_count: number }>();

  return results.map((r) => ({
    anchorKey: r.anchor_key,
    idx: r.idx,
    title: r.title,
    wordCount: r.word_count,
  }));
}

export async function chapterOf(
  db: D1Database,
  slug: string,
  anchorKey: string,
): Promise<Chapter | null> {
  const row = await db
    .prepare(
      `SELECT c.anchor_key, c.idx, c.title, c.html, c.word_count,
              n.audio_key AS narration_audio_key,
              n.duration_s AS narration_duration_s,
              n.cues_json AS narration_cues_json,
              m.uploaded_at AS narration_uploaded_at
         FROM chapter c
         LEFT JOIN chapter_narration n
           ON n.slug = c.slug AND n.anchor_key = c.anchor_key
         LEFT JOIN media_asset m
           ON m.key = n.audio_key
        WHERE c.slug = ?1 AND c.anchor_key = ?2 LIMIT 1`,
    )
    .bind(slug, anchorKey)
    .first<{
      anchor_key: string;
      idx: number;
      title: string;
      html: string;
      word_count: number;
      narration_audio_key: string | null;
      narration_duration_s: number | null;
      narration_cues_json: string | null;
      narration_uploaded_at: string | null;
    }>();

  if (row === null) return null;

  return {
    anchorKey: row.anchor_key,
    idx: row.idx,
    title: row.title,
    html: row.html,
    wordCount: row.word_count,
    narration:
      row.narration_audio_key !== null && row.narration_uploaded_at !== null
        ? {
            audioKey: row.narration_audio_key,
            durationS: row.narration_duration_s,
            cues: parseNarrationCues(row.narration_cues_json),
          }
        : null,
  };
}

function parseNarrationCues(source: string | null): ChapterNarrationCue[] {
  if (source === null) return [];
  try {
    const parsed = JSON.parse(source);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((cue) => ({
        idx: Number(cue.idx),
        blockIndex: cue.blockIndex === undefined ? undefined : Number(cue.blockIndex),
        startS: Number(cue.startS),
        endS: Number(cue.endS),
        text: String(cue.text ?? ""),
      }))
      .filter(
        (cue) =>
          Number.isFinite(cue.idx) &&
          Number.isFinite(cue.startS) &&
          Number.isFinite(cue.endS) &&
          cue.text.trim() !== "",
      );
  } catch {
    return [];
  }
}

/**
 * Every episode, including the ones with no recording.
 *
 * An episode without audio is SHOWN, not hidden. Most of this library is in that
 * state, and hiding them would misreport the shape of the book — a six-episode
 * work would look like a two-episode one.
 */
export async function episodesOf(db: D1Database, slug: string): Promise<Episode[]> {
  const { results } = await db
    .prepare(
      `SELECT e.number, e.title, e.blurb, e.style, e.audio_key, e.transcript_key,
              e.duration_s, e.session_number,
              (SELECT m.uploaded_at FROM media_asset m WHERE m.key = e.audio_key) AS uploaded_at,
              (SELECT m.uploaded_at FROM media_asset m WHERE m.key = e.transcript_key)
                AS transcript_uploaded_at
       FROM episode e WHERE e.slug = ? ORDER BY e.number`,
    )
    .bind(slug)
    .all<{
      number: number;
      title: string;
      blurb: string | null;
      style: string | null;
      audio_key: string | null;
      transcript_key: string | null;
      duration_s: number | null;
      session_number: number | null;
      uploaded_at: string | null;
      transcript_uploaded_at: string | null;
    }>();

  const bridge = await db
    .prepare(`SELECT number, anchor_key FROM episode_chapter WHERE slug = ?`)
    .bind(slug)
    .all<{ number: number; anchor_key: string }>();

  const covered = new Map<number, string[]>();
  for (const row of bridge.results) {
    covered.set(row.number, [...(covered.get(row.number) ?? []), row.anchor_key]);
  }

  return results.map((r) => ({
    number: r.number,
    title: r.title,
    blurb: r.blurb,
    style: r.style,
    audioKey: r.audio_key,
    durationS: r.duration_s,
    hasAudio: r.audio_key !== null && r.uploaded_at !== null,
    // Offered only once the file is actually in R2, exactly as the audio is. A
    // key whose object has not been uploaded would render as a transcript panel
    // that never fills.
    transcriptKey:
      r.transcript_key !== null && r.transcript_uploaded_at !== null ? r.transcript_key : null,
    chapters: covered.get(r.number) ?? [],
    sessionNumber: r.session_number,
  }));
}

/**
 * Episodes arranged into their sessions.
 *
 * Every episode comes back exactly once. Ones outside any session — or all of
 * them, for a book that was never grouped — land in a trailing session numbered
 * 0 with an empty title, which the page renders as a plain list with no heading.
 * That keeps "grouped" and "ungrouped" a rendering difference rather than two
 * code paths, and makes it impossible for an episode to be silently dropped by
 * having no session to belong to.
 */
export async function sessionsOf(db: D1Database, slug: string): Promise<Session[]> {
  const [{ results: named }, episodes] = await Promise.all([
    db
      .prepare(`SELECT number, title FROM book_session WHERE slug = ? ORDER BY number`)
      .bind(slug)
      .all<{ number: number; title: string }>(),
    episodesOf(db, slug),
  ]);

  const sessions: Session[] = named.map((s) => ({
    number: s.number,
    title: s.title,
    episodes: episodes.filter((e) => e.sessionNumber === s.number),
  }));

  const loose = episodes.filter(
    (e) => e.sessionNumber === null || !named.some((s) => s.number === e.sessionNumber),
  );
  if (loose.length > 0) sessions.push({ number: 0, title: "", episodes: loose });

  return sessions.filter((s) => s.episodes.length > 0);
}

/**
 * Every slide deck this book has, in order, each with its pages.
 *
 * A book used to be assumed to have ONE deck, because the only book that had any
 * had one. The pipeline's default is per-chapter and always was — Ayyuha
 * al-Walad has four — so this groups.
 *
 * `deck_id` is NULL for every row written before migration 0010, and those rows
 * are not wrong: they are from a world with one deck in it. They collect into a
 * single untitled deck, which is exactly how they should render, so the site is
 * correct the moment the migration lands and before anything is re-published.
 *
 * Ordered by `deck_id` then `key`, and `key` ends in `page-NN.jpg` zero-padded by
 * pdftoppm, so lexical order is page order.
 */
export async function deckPagesOf(db: D1Database, slug: string): Promise<Deck[]> {
  const { results } = await db
    .prepare(
      `SELECT key, uploaded_at, deck_id, deck_title FROM media_asset
       WHERE slug = ? AND kind = 'deck-page' ORDER BY deck_id, key`,
    )
    .bind(slug)
    .all<{
      key: string;
      uploaded_at: string | null;
      deck_id: string | null;
      deck_title: string | null;
    }>();

  const decks = new Map<string, Deck>();
  for (const r of results) {
    const id = r.deck_id ?? "";
    let deck = decks.get(id);
    if (deck === undefined) {
      deck = { id, title: r.deck_title, pages: [] };
      decks.set(id, deck);
    }
    // The first row that carries a title wins. A deck whose pages disagree is not
    // a case worth modelling — they are written together, from one source.
    if (deck.title === null && r.deck_title !== null) deck.title = r.deck_title;
    deck.pages.push({ key: r.key, available: r.uploaded_at !== null });
  }

  return [...decks.values()];
}

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
  titleArabic: string | null;
}

export interface CardPlayableEpisode {
  slug: string;
  number: number;
  title: string;
  audioKey: string;
  durationS: number | null;
  transcriptKey: string | null;
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
              d.title_arabic,
              -- TWO facts, deliberately not collapsed: the print edition exists,
              -- and it is in R2 so the link works. This used to be one column
              -- (pdf_ready, uploaded only), which meant the card could not say
              -- "not uploaded yet" the way the book page does — it either
              -- promised a download or said nothing. Both are now carried and
              -- describeContents decides the wording for both surfaces.
              (SELECT count(*) FROM media_asset m WHERE m.key = d.pdf_key) AS pdf_exists,
              (SELECT count(*) FROM media_asset m
                WHERE m.key = d.pdf_key AND m.uploaded_at IS NOT NULL) AS pdf_ready,
              (SELECT count(*)          FROM chapter c WHERE c.slug = u.slug) AS chapters,
              (SELECT c.anchor_key       FROM chapter c
                WHERE c.slug = u.slug ORDER BY c.idx LIMIT 1) AS first_chapter_key,
              (SELECT coalesce(sum(c.word_count), 0) FROM chapter c WHERE c.slug = u.slug) AS words,
              (SELECT count(*)          FROM episode e WHERE e.slug = u.slug) AS episodes,
              (SELECT count(*)          FROM episode e
                 JOIN media_asset m ON m.key = e.audio_key
                WHERE e.slug = u.slug AND m.uploaded_at IS NOT NULL) AS recorded,
              (SELECT count(*)          FROM media_asset m
                WHERE m.slug = u.slug AND m.kind = 'deck-page') AS deck_pages,
              (SELECT count(*)          FROM media_asset m
                WHERE m.slug = u.slug AND m.kind = 'deck-page'
                  AND m.uploaded_at IS NOT NULL) AS deck_ready
       FROM content_unit u
       LEFT JOIN unit_detail d ON d.slug = u.slug
       WHERE u.slug IN (${placeholders})`,
    )
    .bind(...slugs)
    .all<{
      slug: string;
      title_arabic: string | null;
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
      titleArabic: r.title_arabic,
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
                WHEN e.transcript_key IS NOT NULL AND transcript.uploaded_at IS NOT NULL
                THEN e.transcript_key
                ELSE NULL
              END AS transcript_key
         FROM episode e
         JOIN media_asset audio
           ON audio.key = e.audio_key
          AND audio.uploaded_at IS NOT NULL
         LEFT JOIN media_asset transcript
           ON transcript.key = e.transcript_key
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
    });
    episodes.set(r.slug, slot);
  }

  return episodes;
}

export interface MediaRow {
  key: string;
  slug: string;
  contentType: string;
  bytes: number;
  uploadedAt: string | null;
}

/**
 * Look a media key up by its key alone.
 *
 * The row carries its own `slug`, and the caller checks THAT against the
 * viewer's grants rather than trusting the slug in the URL. The two are the same
 * today because the key begins with the slug, but a key format that ever stopped
 * being self-describing would silently turn a URL segment into an authorisation
 * claim, which is the shape of every path-traversal bug.
 */
export async function mediaByKey(db: D1Database, key: string): Promise<MediaRow | null> {
  const row = await db
    .prepare(
      `SELECT key, slug, content_type, bytes, uploaded_at FROM media_asset WHERE key = ? LIMIT 1`,
    )
    .bind(key)
    .first<{
      key: string;
      slug: string;
      content_type: string;
      bytes: number;
      uploaded_at: string | null;
    }>();

  if (row === null) return null;

  return {
    key: row.key,
    slug: row.slug,
    contentType: row.content_type,
    bytes: row.bytes,
    uploadedAt: row.uploaded_at,
  };
}
