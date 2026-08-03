import {
  faBookOpen,
  faClock,
  faDownload,
  faFileLines,
  faHeadphones,
  faImages,
  faPause,
  faPlay,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import type { Route } from "./+types/book.$slug";
import { Icon } from "~/components/Icon";
import { SiteFooter } from "~/components/SiteFooter";
import { SiteHeader } from "~/components/SiteHeader";
import { clock, usePlayer } from "~/components/player/Player";
import { cloudflare } from "~/context";
import { notFound } from "~/middleware/deny";
import { requireUnitAccess } from "~/middleware/entitled";
import { session } from "~/middleware/session";
import { unitBySlug } from "~/server/access.server";
import { readingMinutes } from "~/lib/reading";
import {
  chaptersOf,
  deckPagesOf,
  detailOf,
  sessionsOf,
  type Session,
} from "~/server/catalog.server";

/**
 * Layer 4. The gate is here rather than on a shared parent so it can read
 * `params.slug` directly instead of re-deriving it from the URL.
 *
 * Because it is MIDDLEWARE, the `_routes` single-fetch filter cannot skip it:
 * `filterMatchesToLoad` (single-fetch.js:79-84) selects which LOADERS run, and
 * middleware wraps the whole call. A gate written as a parent loader would fall
 * to `GET /book/x.data?_routes=routes/book.$slug`.
 */
export const middleware: Route.MiddlewareFunction[] = [requireUnitAccess];

export async function loader({ params, context }: Route.LoaderArgs) {
  const { env } = context.get(cloudflare);
  const slug = params.slug;

  const unit = await unitBySlug(env.DB, slug);

  // Unreachable in practice — the middleware already proved it is readable —
  // but the loader must not assume that, or a future change to the gate turns
  // into a null dereference here.
  if (unit === null) notFound();

  const [detail, chapters, sessions, deck] = await Promise.all([
    detailOf(env.DB, slug),
    chaptersOf(env.DB, slug),
    sessionsOf(env.DB, slug),
    deckPagesOf(env.DB, slug),
  ]);

  return {
    unit,
    detail,
    chapters,
    sessions,
    deckPages: deck.length,
    deckAvailable: deck.some((p) => p.available),
    isAdmin: context.get(session).viewer!.isAdmin,
  };
}

export default function BookDetail({ loaderData }: Route.ComponentProps) {
  const { unit, detail, chapters, sessions, deckPages, deckAvailable, isAdmin } = loaderData;

  const totalWords = chapters.reduce((n, c) => n + c.wordCount, 0);
  const episodes = sessions.flatMap((s) => s.episodes);
  const withAudio = episodes.filter((e) => e.hasAudio).length;

  // What this book HAS decides the shape of the page. A book with no podcast
  // gets no Listen column at all rather than an empty one — a column reading
  // "no episodes" is a fault report where its absence is simply a fact. The
  // two-column split therefore needs BOTH halves to be real, and "real" for the
  // podcast means at least one episode you can actually play.
  const canRead = chapters.length > 0;
  const canListen = withAudio > 0;
  const bothHalves = canRead && canListen;

  return (
    <div className="pf-shell">
      <SiteHeader here="book" isAdmin={isAdmin} />

      <main id="main" className="pf-container">
        {/* ---- Identity ----
            The same two-part identity the library card carries, opened out: the
            Arabic title set large as the book's own name, the English beneath
            it. */}
        <header className="pf-masthead pf-masthead--tight">
          <p className="pf-eyebrow">
            {unit.bucket}
            {detail?.editionNote ? ` · ${detail.editionNote.replace(/_/g, " ")}` : null}
          </p>

          {detail?.titleArabic ? (
            <p lang="ar" dir="rtl" className="pf-book-title-ar">
              {detail.titleArabic}
            </p>
          ) : null}

          <h1 className="pf-title pf-title--sm">{unit.title}</h1>

          {/* Rendered at publish time, not here — italics, inline Arabic and the
              folded transliteration all come from the same renderer as the
              chapters, so the blurb reads exactly as the book does. */}
          {detail?.blurbHtml ? (
            <div
              className="reader pf-blurb"
              dangerouslySetInnerHTML={{ __html: detail.blurbHtml }}
            />
          ) : null}

          {/* ---- What this book actually has ----
              One pill per fact, and only for facts that are true. Most books in
              this library are missing most things, and a greyed-out icon reads
              as a fault where a named pill reads as a fact. */}
          <ul className="pf-pills">
            {describeContents({
              chapters: chapters.length,
              words: totalWords,
              episodes: episodes.length,
              withAudio,
              pdf: Boolean(detail?.pdfKey),
              pdfAvailable: Boolean(detail?.pdfAvailable),
              deckPages,
              deckAvailable,
            }).map((fact) => (
              <li key={fact.label} className="pf-pill pf-pill--outline">
                <Icon icon={fact.icon} />
                {fact.label}
              </li>
            ))}
          </ul>

          {/* A link is offered ONLY when the file is actually in R2. The row
              exists as soon as the PDF is on the author's disk, and linking to
              that would promise a download that 404s. */}
          {detail?.pdfKey && detail.pdfAvailable ? (
            <p className="pf-masthead__action">
              <a href={`/media/${detail.pdfKey}`} className="pf-button">
                <Icon icon={faDownload} />
                Download the print edition
                <span className="pf-button__meta">{megabytes(detail.pdfBytes)}</span>
              </a>
            </p>
          ) : null}
        </header>

        {/* ---- What there is of this book ----
            Two columns only when there are two things. One half alone gets the
            full width and reads as a complete page rather than a page with a
            hole in it. */}
        <div className={bothHalves ? "pf-grid pf-grid--pair" : "pf-single"}>
          {canRead ? <ReadingEdition slug={unit.slug} chapters={chapters} /> : null}
          {canListen ? (
            <Podcast
              slug={unit.slug}
              bookTitle={unit.title}
              sessions={sessions}
              chapters={chapters}
              alongsideAnEdition={bothHalves}
            />
          ) : null}
          {!canRead && !canListen ? (
            <p className="pf-note">Nothing of this book is readable or listenable yet.</p>
          ) : null}
        </div>

        {deckPages > 0 ? (
          <section className="pf-section pf-section--ruled">
            <div className="pf-section__head">
              <h2 className="pf-section__title">
                <Icon icon={faImages} />
                Slides
              </h2>
              <span className="pf-section__count">{deckPages} pages</span>
            </div>
            <p className="pf-note pf-section__intro">
              {deckAvailable
                ? "A deck for the whole book."
                : "A deck exists for this book but has not been uploaded yet."}
            </p>
            {deckAvailable ? (
              <p className="pf-masthead__action">
                <Link to={`/book/${unit.slug}/slides`} className="pf-button">
                  <Icon icon={faImages} />
                  Open the deck
                </Link>
              </p>
            ) : null}
          </section>
        ) : null}
      </main>

      <SiteFooter />
    </div>
  );
}

/**
 * The chapters-and-episodes problem, stated rather than hidden.
 *
 * The reading edition and the podcast are drawn along DIFFERENT lines from the
 * same source — this book is nine chapters and twenty episodes — and a reader
 * who is not told that concludes the site is broken or that there are two
 * different products. So both lists sit on one page, side by side, each labelled
 * with its own count, under one title.
 */
function ReadingEdition({
  slug,
  chapters,
}: {
  slug: string;
  chapters: Route.ComponentProps["loaderData"]["chapters"];
}) {
  if (chapters.length === 0) {
    return (
      <section className="pf-section">
        <SectionHeading icon={faBookOpen} title="Read" count="no reading edition yet" />
        <p className="pf-note pf-section__intro">
          The translated edition of this book has not been published here yet.
        </p>
      </section>
    );
  }

  return (
    <section className="pf-section">
      <SectionHeading icon={faBookOpen} title="Read" count={`${chapters.length} chapters`} />

      <ol className="pf-rows pf-section__intro">
        {chapters.map((chapter) => (
          <li key={chapter.anchorKey}>
            {/* No ordinal column. The heading already carries the book's OWN
                number where it has one ("3. The Hours Before Dawn"), and our
                position counts the introduction as the first entry — so the two
                disagreed by one on every line. The book's numbering wins. */}
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(chapter.anchorKey)}`}
              className="pf-row"
            >
              <span className="pf-row__main">{chapter.title}</span>
              <span className="pf-row__meta">{readingMinutes(chapter.wordCount)} min</span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * The podcast, grouped into the sessions the author declared.
 *
 * A session heading is rendered only when the session HAS a title — the
 * catalog puts ungrouped episodes in a titleless session numbered 0, so a book
 * that was never grouped renders as one plain list without any special case
 * here. That is why there is no `if (grouped)` branch in this component.
 */
function Podcast({
  slug,
  bookTitle,
  sessions,
  chapters,
  alongsideAnEdition,
}: {
  slug: string;
  bookTitle: string;
  sessions: Session[];
  chapters: Route.ComponentProps["loaderData"]["chapters"];
  alongsideAnEdition: boolean;
}) {
  const titleOf = new Map(chapters.map((c) => [c.anchorKey, c.title]));
  const episodes = sessions.flatMap((s) => s.episodes);
  const withAudio = episodes.filter((e) => e.hasAudio).length;
  const grouped = sessions.some((s) => s.title !== "");

  return (
    <section className="pf-section">
      <SectionHeading
        icon={faHeadphones}
        title="Listen"
        count={[
          grouped ? `${sessions.length} sessions` : null,
          withAudio === episodes.length
            ? `${episodes.length} episodes`
            : `${withAudio} of ${episodes.length} episodes`,
        ]
          .filter(Boolean)
          .join(" · ")}
      />

      {/* Only worth saying when both lists are on screen. On a page with no
          reading edition there is nothing for the reader to be confused with. */}
      {alongsideAnEdition ? (
        <p className="pf-note pf-note--quiet pf-section__intro">
          The episodes are drawn along different lines from the chapters — they
          are two readings of the same book, not two halves of one.
        </p>
      ) : null}

      {sessions.map((session) => (
        <div key={session.number} className="pf-session">
          {/* Label and title are separate flex items, not one wrapping line of
              inline spans. A long title used to wrap back to the left margin and
              set its second line under "SESSION 3", so the two read as unrelated
              fragments — three of this book's five headings did it on a phone. */}
          {session.title ? (
            <h3 className="pf-session__head">
              <span className="pf-session__label">Session {session.number}</span>
              <span className="pf-session__title">{session.title}</span>
            </h3>
          ) : null}

          <ol className="pf-rows pf-session__list">
            {session.episodes.map((episode) => (
              <li key={episode.number}>
                <div className="pf-row">
                  <span className="pf-row__index">{episode.number}</span>

                  <div className="pf-row__main">
                    <p>{episode.title}</p>

                    {episode.chapters.length > 0 ? (
                      <p className="pf-note pf-note--quiet">
                        Read along:{" "}
                        {episode.chapters.map((key) => titleOf.get(key) ?? key).join(", ")}
                      </p>
                    ) : null}
                  </div>

                  {episode.hasAudio && episode.audioKey !== null ? (
                    <PlayButton
                      episode={episode}
                      onPlay={(p) => p.play({
                        slug,
                        bookTitle,
                        number: episode.number,
                        title: episode.title,
                        src: `/media/${episode.audioKey}`,
                        durationS: episode.durationS,
                      })}
                    />
                  ) : (
                    <span className="pf-row__meta">not recorded</span>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </section>
  );
}

/** Shows a pause glyph when this is the episode currently playing. */
function PlayButton({
  episode,
  onPlay,
}: {
  episode: Session["episodes"][number];
  onPlay: (player: ReturnType<typeof usePlayer>) => void;
}) {
  const player = usePlayer();
  const isCurrent = player.current?.src === `/media/${episode.audioKey}`;

  return (
    <button
      type="button"
      onClick={() => (isCurrent ? player.toggle() : onPlay(player))}
      aria-pressed={isCurrent}
      className="pf-button pf-button--sm pf-row__action"
    >
      <Icon icon={isCurrent && player.playing ? faPause : faPlay} />
      {isCurrent && player.playing ? "Pause" : "Play"}{" "}
      {episode.durationS ? clock(episode.durationS) : ""}
    </button>
  );
}

function SectionHeading({
  icon,
  title,
  count,
}: {
  icon: IconDefinition;
  title: string;
  count: string;
}) {
  return (
    <div className="pf-section__head">
      <h2 className="pf-section__title">
        <Icon icon={icon} />
        {title}
      </h2>
      <span className="pf-section__count">{count}</span>
    </div>
  );
}

/** One fact about a book: an icon that speeds recognition, and the word that carries it. */
interface Fact {
  icon: IconDefinition;
  label: string;
}

/**
 * What this book contains, one honest fact at a time.
 *
 * Returns the facts rather than a sentence, because they are rendered as pills
 * now — but the rule they were written under has not changed: "exists" and "can
 * be opened" are different facts and are said differently. Most of this library
 * is half-produced, and a reader who is told a print edition is here and then
 * cannot open it concludes the site is broken, where a reader told it is not
 * uploaded yet simply knows where things stand.
 *
 * An empty array means nothing is published, and the caller renders no pills at
 * all rather than one that says so — the page already says it elsewhere.
 */
function describeContents(x: {
  chapters: number;
  words: number;
  episodes: number;
  withAudio: number;
  pdf: boolean;
  pdfAvailable: boolean;
  deckPages: number;
  deckAvailable: boolean;
}): Fact[] {
  const facts: Fact[] = [];

  if (x.chapters > 0) {
    facts.push({ icon: faBookOpen, label: `${x.chapters} chapters` });
    facts.push({ icon: faClock, label: `${readingMinutes(x.words)} min read` });
  }
  if (x.episodes > 0) {
    facts.push({
      icon: faHeadphones,
      label:
        x.withAudio === 0
          ? `${x.episodes} episodes planned`
          : x.withAudio === x.episodes
            ? `${x.episodes} episodes`
            : `${x.withAudio} of ${x.episodes} episodes`,
    });
  }
  if (x.pdf) {
    facts.push({
      icon: faFileLines,
      label: x.pdfAvailable ? "print edition" : "print edition, not uploaded yet",
    });
  }
  if (x.deckPages > 0) {
    facts.push({
      icon: faImages,
      label: x.deckAvailable
        ? `${x.deckPages}-page deck`
        : `${x.deckPages}-page deck, not uploaded yet`,
    });
  }

  return facts;
}

function megabytes(bytes: number | null | undefined): string {
  if (!bytes) return "";
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}
