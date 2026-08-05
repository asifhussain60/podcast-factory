import {
  faBookOpen,
  faClock,
  faFileLines,
  faHeadphones,
  faImages,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";

import { count } from "~/lib/plural";
import { readingMinutes } from "~/lib/reading";

/** One fact about a book: an icon that speeds recognition, and the word that carries it. */
export interface Fact {
  icon: IconDefinition;
  label: string;
}

/**
 * What a book contains, said once, so the grid and the book page cannot disagree.
 *
 * They did. The library card and the book page each had their own version of this
 * list, and the two answered the same question differently in three ways:
 *
 *   - the card said "PDF" and "slides"; the page said "print edition" and
 *     "15-page deck";
 *   - the page distinguished a file that EXISTS from one that can be OPENED and
 *     the card did not, so a card offered a download that 404s;
 *   - reading time was computed server-side for the card and client-side for the
 *     page, with different handling of zero, so a book with no words showed no
 *     pill on its card and "1 min read" on its own page.
 *
 * None of that was a bug anyone wrote. It is what two implementations of one
 * sentence become. The wording kept here is the book page's, because it is the
 * more precise of the two and it is the one that never promises a broken link.
 *
 * THE RULE THIS INHERITS, unchanged: name only what EXISTS. Most of this library
 * is missing most things, and a row of icons with the absent ones greyed out reads
 * as a fault report where naming only what is there reads as a fact — a book with
 * one pill does not look broken.
 *
 * "Exists" and "can be opened" stay DIFFERENT facts and are still said
 * differently. A reader told a print edition is here who then cannot open it
 * concludes the site is broken; a reader told it is not uploaded yet simply knows
 * where things stand.
 *
 * An empty array means nothing is published, and the caller renders no pills at
 * all rather than one that says so.
 */
export function describeContents(x: {
  chapters: number;
  /** Raw word count, never a precomputed minute figure — see `readingMinutes`. */
  words: number;
  episodes: number;
  /** Episodes whose recording is in R2, not merely on someone's disk. */
  withAudio: number;
  /** A print edition exists at all. */
  pdf: boolean;
  /** ...and is in R2, so the link works. */
  pdfAvailable: boolean;
  deckPages: number;
  /** At least one deck page is in R2. */
  deckAvailable: boolean;
}, { combineFormats = false }: { combineFormats?: boolean } = {}): Fact[] {
  const facts: Fact[] = [];

  if (x.chapters > 0) {
    facts.push({ icon: faBookOpen, label: count(x.chapters, "chapter") });

    // Gated on WORDS, not on chapters. Chapters that carry no counted words
    // (a stub, a chapter whose count never ran) would otherwise print the
    // one-minute floor `readingMinutes` applies, which is a reading time
    // invented out of nothing.
    if (x.words > 0) {
      facts.push({ icon: faClock, label: `${readingMinutes(x.words)} min read` });
    }
  }

  if (x.episodes > 0) {
    facts.push({
      icon: faHeadphones,
      label:
        x.withAudio === 0
          ? count(x.episodes, "episode planned", "episodes planned")
          : x.withAudio === x.episodes
            ? count(x.episodes, "episode")
            : `${x.withAudio} of ${count(x.episodes, "episode")}`,
    });
  }

  // THE TWO FORMATS, together or apart.
  //
  // Apart on the book page, which has the room and where the reader is deciding
  // what to open. Together on a library CARD, where five facts wrapped to three
  // rows while every other book had four or fewer — so no two cards were the
  // same height and the grid did not line up.
  //
  // Combining loses nothing: both are still named in words, which is the rule
  // this list has always followed. Swapping them for bare glyphs would have been
  // shorter and would have rebuilt the thing that rule exists to prevent — a row
  // of symbols where the reader guesses, and where absence reads as fault.
  if (combineFormats) {
    // Compact ONLY when both are present and have to share a pill. A book with
    // one format has the room for its natural name, and "print" alone reads like
    // an abbreviation of something.
    const both = x.pdf && x.deckPages > 0;
    const parts: string[] = [];
    if (x.pdf) parts.push(both ? "print" : "print edition");
    if (x.deckPages > 0) parts.push(count(x.deckPages, "slide"));

    if (parts.length > 0) {
      // One caveat for the pair rather than one each. The card is a summary; the
      // book page says precisely which of the two is not in R2 yet.
      const waiting = (x.pdf && !x.pdfAvailable) || (x.deckPages > 0 && !x.deckAvailable);
      facts.push({
        icon: x.pdf ? faFileLines : faImages,
        label: parts.join(" + ") + (waiting ? ", not uploaded yet" : ""),
      });
    }

    return facts;
  }

  if (x.pdf) {
    facts.push({
      icon: faFileLines,
      label: x.pdfAvailable ? "print edition" : "print edition, not uploaded yet",
    });
  }

  if (x.deckPages > 0) {
    // Attributive, so it does not take a plural even at one: "1-page deck".
    facts.push({
      icon: faImages,
      label: x.deckAvailable
        ? `${x.deckPages}-page deck`
        : `${x.deckPages}-page deck, not uploaded yet`,
    });
  }

  return facts;
}
