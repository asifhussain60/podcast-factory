/**
 * book-card-identity.ts — resolve a book's card identity from the BOOK's OWN FILES.
 *
 * Why this exists. Every identity field on a Studio card — Arabic title, English
 * title, author — came from `BOOK_CARD_META`, a hand-maintained TypeScript
 * dictionary keyed by slug. `meta.yml` was never read for card display at all. So
 * a book got a proper card only if a human had typed one, and the shelf was
 * visibly ragged: `degrees-of-excellence` showed "Not yet catalogued" while its
 * own `meta.yml` carried both an author and a full English title, and
 * `mukhtasar-ul-asar-2` showed an author but no title because the dictionary had
 * one and not the other.
 *
 * The card is now DERIVED. A book that records who wrote it gets an author on its
 * card, without anyone maintaining a parallel list. `BOOK_CARD_META` stays as a
 * FALLBACK — it holds real curation (icons, blurbs, and the only Arabic titles
 * that exist anywhere in the repo today) — and loses to the book's own files
 * wherever both speak.
 *
 * The author key is genuinely non-uniform on disk, which is why this reads three
 * places rather than one: top-level `author` (kunooz, mukhtasar-2),
 * `doctrinal_context.author` (degrees-of-excellence, master-and-disciple), and
 * `_system/meta.yml`'s `author` (ayyuhal-walad). Normalizing the FILES would be a
 * bigger, riskier change than normalizing the read, and the pipeline writes all
 * three shapes today.
 */

import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse } from "yaml";

import { cardMetaFor, type ResolvedCardMeta } from "../book-card-meta";
import { simplifyTransliteration } from "../translit";

/** Every slot a card can show. Missing values are `undefined`, never omitted —
 *  the template renders a placeholder rather than collapsing the row. */
export interface BookCardIdentity {
  /** Arabic (or other native-script) title. */
  nativeTitle?: string;
  nativeLang?: "ar" | "ur" | "zh";
  /** The English title shown as the card's heading. Always present. */
  title: string;
  author?: string;
  icon: string;
  blurb?: string;
  volume?: number;
  /**
   * The book's subject track, shown as the card's corner ribbon.
   *
   * The SAME `study_track` field the Podcast Factory Library publishes from
   * (scripts/podcast/_listener_book.py reads it out of this very file), so the
   * ribbon here and the ribbon there cannot disagree about what a book is.
   * `undefined` when the book does not say — never guessed from the bucket,
   * which answers a different question.
   */
  studyTrack?: StudyTrack;
  /** True when NOTHING beyond the slug is known — the honest empty state. */
  uncatalogued: boolean;
}

/**
 * The five tracks, spelled the same as the Library's `app/lib/study-track.ts`
 * and as the CHECK constraint on `unit_detail.study_track`. Kept as a literal
 * union rather than imported: the two apps are separate builds, and this is a
 * short closed list whose drift the validator below turns into an absent
 * ribbon rather than a broken one.
 */
export type StudyTrack =
  "theology" | "history" | "shariah" | "esoteric" | "reality";

const STUDY_TRACKS: readonly string[] = [
  "theology",
  "history",
  "shariah",
  "esoteric",
  "reality",
];

/** A track only when the file names one this app can actually paint. */
function studyTrack(value: unknown): StudyTrack | undefined {
  const s = str(value);
  return s && STUDY_TRACKS.includes(s) ? (s as StudyTrack) : undefined;
}

async function readYaml(path: string): Promise<Record<string, unknown> | null> {
  try {
    const doc = parse(await readFile(path, "utf-8"));
    return doc && typeof doc === "object"
      ? (doc as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function str(value: unknown): string | undefined {
  const s = typeof value === "string" ? value.trim() : "";
  return s || undefined;
}

function nested(
  doc: Record<string, unknown> | null,
  outer: string,
  inner: string,
): string | undefined {
  const o = doc?.[outer];
  return o && typeof o === "object"
    ? str((o as Record<string, unknown>)[inner])
    : undefined;
}

/** Contains Arabic script. A `title` that is already Arabic IS the native title. */
function isArabic(s: string | undefined): boolean {
  return !!s && /[؀-ۿ]/.test(s);
}

/**
 * Identity for one book directory.
 *
 * `slugTitle` is the caller's slug-derived fallback, so this module does not need
 * to know how a slug becomes a title.
 */
export async function resolveBookCardIdentity(
  slug: string,
  dir: string,
  slugTitle: string,
): Promise<BookCardIdentity> {
  const fallback: ResolvedCardMeta = cardMetaFor(slug);
  const meta = await readYaml(join(dir, "meta.yml"));
  const sysMeta = await readYaml(join(dir, "_system", "meta.yml"));
  const work = await readYaml(join(dir, "..", "work.yml"));

  const author =
    str(meta?.author) ??
    nested(meta, "doctrinal_context", "author") ??
    str(sysMeta?.author) ??
    nested(meta, "publication", "author") ??
    str(work?.author) ??
    fallback.author;

  // `title_arabic` is the field this repo now records an Arabic title in. Before
  // 2026-08-02 no meta.yml carried one at all, so the hand-typed map is still the
  // only source for most books — hence the fallback rather than a straight read.
  // A `title`/`original_title` that is ITSELF Arabic script counts too; a
  // transliterated `original_title` ("Kitab ithbat al-imama") deliberately does
  // not, since a romanization is exactly what the native slot is not for.
  const nativeFromMeta =
    str(meta?.title_arabic) ??
    str(work?.title_arabic) ??
    [str(meta?.title), str(meta?.original_title)].find(isArabic);

  // The SHORT title wins on a card. `publication.english_title` is the title-page
  // form and carries the subtitle — "Degrees of Excellence: A Fatimid Treatise on
  // Leadership in Islam" is 64 characters and wraps to four lines in a card that
  // is meant to look like its neighbours. It is the last resort, not the first.
  const englishTitle =
    fallback.displayTitle ??
    (isArabic(str(meta?.title)) ? undefined : str(meta?.title)) ??
    str(work?.title) ??
    nested(meta, "publication", "english_title") ??
    slugTitle;

  const nativeTitle = nativeFromMeta ?? fallback.nativeTitle;
  const originalLanguage =
    str(meta?.original_title_language) ?? str(meta?.source_language);

  return {
    nativeTitle,
    nativeLang: nativeTitle
      ? (fallback.nativeLang ??
        (originalLanguage === "ur"
          ? "ur"
          : isArabic(nativeTitle)
            ? "ar"
            : "zh"))
      : undefined,
    title: simplifyTransliteration(englishTitle),
    author: author ? simplifyTransliteration(author) : undefined,
    icon: fallback.icon ?? "fa-book",
    blurb: fallback.blurb,
    volume: fallback.volume,
    // The book's own file wins; the series' work.yml is the default for a work
    // whose volumes carry no metadata of their own (al-anwaar-al-lateefah is
    // split into six, and only vol-01 has a meta.yml). There is no third
    // source and deliberately no guess: a book that names no track gets no
    // ribbon rather than one inferred from its shelf.
    studyTrack: studyTrack(meta?.study_track) ?? studyTrack(work?.study_track),
    // Honest only when the book itself says nothing either. This used to be true
    // whenever the hand-typed map had no row, which is why a book carrying an
    // author and an English title on disk still read "Not yet catalogued".
    uncatalogued:
      !nativeTitle &&
      !author &&
      !nested(meta, "publication", "english_title") &&
      !fallback.displayTitle,
  };
}
