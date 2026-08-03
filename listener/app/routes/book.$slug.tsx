import { Link } from "react-router";

import type { Route } from "./+types/book.$slug";
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
    <div className="min-h-dvh bg-pf-bg">
      <SiteHeader here="book" isAdmin={isAdmin} />

      <main id="main" className="mx-auto max-w-5xl px-6 pb-32">
        {/* ---- Identity ---- */}
        <header className="border-t border-pf-rule pt-12">
          <p className="font-ui text-xs uppercase tracking-[0.18em] text-pf-faint">
            {unit.bucket}
            {detail?.editionNote ? ` · ${detail.editionNote.replace(/_/g, " ")}` : null}
          </p>

          <h1 className="mt-3 max-w-3xl text-balance font-prose text-4xl leading-[1.1] text-pf-ink sm:text-5xl">
            {unit.title}
          </h1>

          {detail?.titleArabic ? (
            <p
              lang="ar"
              dir="rtl"
              className="mt-3 text-left font-arabic text-3xl text-pf-muted"
            >
              {detail.titleArabic}
            </p>
          ) : null}

          {/* Rendered at publish time, not here — italics, inline Arabic and the
              folded transliteration all come from the same renderer as the
              chapters, so the blurb reads exactly as the book does. */}
          {detail?.blurbHtml ? (
            <div
              className="reader mt-6 max-w-2xl text-pf-muted"
              dangerouslySetInnerHTML={{ __html: detail.blurbHtml }}
            />
          ) : null}
        </header>

        {/* ---- What this book actually has ----
            Named honestly rather than shown as a row of icons: most books in
            this library are missing most things, and a greyed-out icon reads as
            a fault where a sentence reads as a fact. */}
        <p className="mt-8 font-ui text-sm text-pf-muted">
          {describeContents({
            chapters: chapters.length,
            words: totalWords,
            episodes: episodes.length,
            withAudio,
            pdf: Boolean(detail?.pdfKey),
            pdfAvailable: Boolean(detail?.pdfAvailable),
            deckPages,
            deckAvailable,
          })}
        </p>

        {/* A link is offered ONLY when the file is actually in R2. The row exists
            as soon as the PDF is on the author's disk, and linking to that would
            promise a download that 404s. */}
        {detail?.pdfKey && detail.pdfAvailable ? (
          <p className="mt-4">
            <a
              href={`/media/${detail.pdfKey}`}
              className="inline-flex items-center gap-2 rounded-lg border border-pf-rule bg-pf-surface px-4 py-2 font-ui text-sm text-pf-ink no-underline transition-colors hover:border-pf-accent"
            >
              Download the print edition
              <span className="text-pf-muted">{megabytes(detail.pdfBytes)}</span>
            </a>
          </p>
        ) : null}

        {/* ---- What there is of this book ----
            Two columns only when there are two things. One half alone gets the
            full width and reads as a complete page rather than a page with a
            hole in it. */}
        <div
          className={[
            "mt-16",
            bothHalves ? "grid gap-14 lg:grid-cols-2 lg:gap-12" : "max-w-2xl",
          ].join(" ")}
        >
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
            <p className="font-ui text-sm text-pf-muted">
              Nothing of this book is readable or listenable yet.
            </p>
          ) : null}
        </div>

        {deckPages > 0 ? (
          <section className="mt-16 border-t border-pf-rule pt-8">
            <h2 className="font-prose text-2xl text-pf-ink">Slides</h2>
            <p className="mt-2 font-ui text-sm text-pf-muted">
              {deckAvailable
                ? `A ${deckPages}-page deck for the whole book.`
                : `A ${deckPages}-page deck exists for this book but has not been uploaded yet.`}
            </p>
            {deckAvailable ? (
              <Link
                to={`/book/${unit.slug}/slides`}
                className="mt-4 inline-block rounded-lg border border-pf-rule bg-pf-surface px-4 py-2 font-ui text-sm text-pf-ink no-underline transition-colors hover:border-pf-accent"
              >
                Open the deck
              </Link>
            ) : null}
          </section>
        ) : null}
      </main>
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
      <section>
        <SectionHeading title="Read" count="no reading edition yet" />
        <p className="mt-4 font-ui text-sm text-pf-muted">
          The translated edition of this book has not been published here yet.
        </p>
      </section>
    );
  }

  return (
    <section>
      <SectionHeading title="Read" count={`${chapters.length} chapters`} />

      <ol className="mt-5 border-t border-pf-rule-soft">
        {chapters.map((chapter) => (
          <li key={chapter.anchorKey} className="border-b border-pf-rule-soft">
            {/* No ordinal column. The heading already carries the book's OWN
                number where it has one ("3. The Hours Before Dawn"), and our
                position counts the introduction as the first entry — so the two
                disagreed by one on every line. The book's numbering wins. */}
            <Link
              to={`/book/${slug}/read/${encodeURIComponent(chapter.anchorKey)}`}
              className="flex items-baseline gap-4 py-3.5 no-underline transition-colors hover:bg-pf-surface"
            >
              <span className="flex-1 font-prose text-pf-ink">{chapter.title}</span>
              <span className="shrink-0 font-ui text-xs text-pf-faint">
                {readingMinutes(chapter.wordCount)} min
              </span>
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
    <section>
      <SectionHeading
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
        <p className="mt-3 font-ui text-sm text-pf-faint">
          The episodes are drawn along different lines from the chapters — they
          are two readings of the same book, not two halves of one.
        </p>
      ) : null}

      {sessions.map((session) => (
        <div key={session.number} className="mt-8 first:mt-5">
          {/* Label and title are separate flex items, not one wrapping line of
              inline spans. A long title used to wrap back to the left margin and
              set its second line under "SESSION 3", so the two read as unrelated
              fragments — three of this book's five headings did it on a phone. */}
          {session.title ? (
            <h3 className="flex flex-wrap gap-x-2 font-ui text-xs text-pf-muted">
              <span className="shrink-0 uppercase tracking-[0.16em]">
                Session {session.number}
                <span className="text-pf-faint"> ·</span>
              </span>
              <span className="min-w-0 flex-1 text-pf-ink">{session.title}</span>
            </h3>
          ) : null}

          <ol className="mt-3 border-t border-pf-rule-soft">
            {session.episodes.map((episode) => (
              <li key={episode.number} className="border-b border-pf-rule-soft py-3.5">
                <div className="flex items-baseline gap-4">
                  <span className="w-6 shrink-0 text-right font-ui text-xs tabular-nums text-pf-faint">
                    {episode.number}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="font-prose text-pf-ink">{episode.title}</p>

                    {episode.chapters.length > 0 ? (
                      <p className="mt-1 font-ui text-xs text-pf-faint">
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
                    <span className="shrink-0 font-ui text-xs text-pf-faint">not recorded</span>
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
      className={[
        "shrink-0 rounded-full border px-3 py-1 font-ui text-xs transition-colors",
        isCurrent
          ? "border-pf-accent text-pf-accent"
          : "border-pf-rule text-pf-ink hover:border-pf-accent",
      ].join(" ")}
    >
      {isCurrent && player.playing ? "Pause" : "Play"}{" "}
      {episode.durationS ? clock(episode.durationS) : ""}
    </button>
  );
}

function SectionHeading({ title, count }: { title: string; count: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <h2 className="font-prose text-2xl text-pf-ink">{title}</h2>
      <span className="font-ui text-xs uppercase tracking-widest text-pf-faint">{count}</span>
    </div>
  );
}

/**
 * One honest sentence about what this book contains.
 *
 * "Exists" and "can be opened" are different facts and are said differently.
 * Most of this library is half-produced, and a reader who is told a print
 * edition is here and then cannot open it concludes the site is broken — where a
 * reader told it is not uploaded yet simply knows where things stand.
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
}): string {
  const parts: string[] = [];

  if (x.chapters > 0) {
    parts.push(`${x.chapters} chapters, about ${readingMinutes(x.words)} minutes of reading`);
  }
  if (x.episodes > 0) {
    parts.push(
      x.withAudio === 0
        ? `${x.episodes} episodes planned, none recorded yet`
        : `${x.withAudio} of ${x.episodes} episodes recorded`,
    );
  }
  if (x.pdf) parts.push(x.pdfAvailable ? "a print edition" : "a print edition, not uploaded yet");
  if (x.deckPages > 0) {
    parts.push(
      x.deckAvailable
        ? `a ${x.deckPages}-page slide deck`
        : `a ${x.deckPages}-page slide deck, not uploaded yet`,
    );
  }

  return parts.length === 0 ? "Nothing has been published for this book yet." : parts.join(" · ");
}

function megabytes(bytes: number | null | undefined): string {
  if (!bytes) return "";
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}
