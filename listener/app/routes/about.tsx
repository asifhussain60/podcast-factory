import { useMemo, useState } from "react";
import { faArrowLeft, faBullhorn } from "@fortawesome/free-solid-svg-icons";

import type { Route } from "./+types/about";
import { AppShell } from "~/components/AppShell";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { SearchBox } from "~/components/SearchBox";
import { ALL_SECTIONS, RELEASES, type Entry, type Section } from "~/lib/about";
import { count } from "~/lib/plural";
import { session } from "~/middleware/session";

/**
 * What this site does — the one page a reader can be pointed at.
 *
 * SIGNED IN, like every other page. It sits inside `_authed` in app/routes.ts and
 * takes its protection from that position, which is the only way anything is
 * protected here. That decision has one consequence worth stating: the link in
 * the invitation message points at this page, so someone following it before they
 * have signed in is bounced to sign-in and returned here afterwards — the gate
 * carries the destination in `?next=`, so the link is not a dead end.
 *
 * The loader reads nothing from the database. Every word on this page is in
 * `lib/about.ts`, so there is no query here that could name a book, and a reader
 * with no books at all still gets the whole page.
 *
 * THE LAYOUT is bands, edge to edge, and the shell is asked for no container at
 * all (`flush`). The first version set everything in one 34rem column down the
 * left of a 1440px window, which is the correct measure for PROSE and the wrong
 * shape for a page: the reader met a narrow grey ribbon with two thirds of the
 * screen empty beside it. What is capped now is the LINE LENGTH inside each band,
 * not the band — so the page fills the window and the sentences stay readable,
 * which are two different problems that one `max-width` was answering as if they
 * were one.
 */

export function meta(): Route.MetaDescriptors {
  return [
    { title: "About — Podcast Factory" },
    {
      name: "description",
      content: "What this library does: reading, listening, highlights, notes and access.",
    },
  ];
}

export function loader({ context }: Route.LoaderArgs) {
  // Only whether to offer the Access link in the masthead. Nothing on this page
  // varies by who is reading it.
  return { isAdmin: context.get(session).viewer?.isAdmin === true };
}

/** Lower-cased text of one entry — everything the search box looks at. */
const haystack = (e: Entry) => `${e.q} ${e.a.join(" ")}`.toLowerCase();

/** The release list as a category, so the cards can offer it like any other. */
const WHATS_NEW = "whats-new";

export default function About({ loaderData }: Route.ComponentProps) {
  const [query, setQuery] = useState("");
  /** `null` is "everything", which is also what searching forces. */
  const [pick, setPick] = useState<string | null>(null);

  const needle = query.trim().toLowerCase();
  const searching = needle !== "";

  /**
   * Typing clears the chosen category.
   *
   * Without this the page narrowed for no visible reason: a search ignores the
   * category (see `shown`), so somebody who had picked Listening, searched, then
   * cleared the box was returned to Listening — with What's new gone and two
   * thirds of the page missing. The search is a question about the whole page, so
   * the page it returns to is the whole page.
   */
  function search(next: string) {
    setQuery(next);
    if (next.trim() !== "") setPick(null);
  }

  /**
   * What to draw, as sections with only their matching entries.
   *
   * Searching IGNORES the chosen category, deliberately. A reader who types
   * "highlight" while Listening is selected and gets nothing has been told, quite
   * wrongly, that the site cannot do it. A search is a question about the whole
   * page.
   */
  const shown = useMemo(() => {
    const scope =
      searching || pick === null ? ALL_SECTIONS : ALL_SECTIONS.filter((s) => s.id === pick);
    if (!searching) return scope;

    return scope
      .map((s) => ({ ...s, entries: s.entries.filter((e) => haystack(e).includes(needle)) }))
      .filter((s) => s.entries.length > 0);
  }, [needle, searching, pick]);

  const hits = shown.reduce((n, s) => n + s.entries.length, 0);

  // "What's new" is a category like any other to the cards, but it holds dated
  // notes rather than questions, so it is not something the search can match. It
  // is hidden while searching rather than shown empty.
  const showReleases = !searching && (pick === null || pick === WHATS_NEW);
  const picked = pick === null ? null : ALL_SECTIONS.find((s) => s.id === pick) ?? null;

  return (
    <AppShell here="about" isAdmin={loaderData.isAdmin} flush>
      {/* ---- The hero, with the search in it ------------------------------
          A prominent search field in the hero is the one thing every help page
          worth copying has in common, and it is the fastest route to an answer
          for somebody who already knows what they want to ask. */}
      <section className="pf-about-hero">
        <div className="pf-about-wrap pf-about-hero__inner">
          <p className="pf-about-hero__eyebrow">Podcast Factory</p>
          <h1 className="pf-about-hero__title">Everything this library can do</h1>
          <p className="pf-about-hero__lead">
            Classical works published twice over — as modern English reading editions, and as
            long-form audio drawn from the same source. Read one, listen to the other, or follow
            both together.
          </p>

          <div className="pf-about-hero__search">
            <SearchBox
              id="about-q"
              label="Search this page"
              placeholder="Search this page"
              size="wide"
              action={{ kind: "filter", value: query, onChange: search }}
            />
          </div>
        </div>
      </section>

      {/* ---- Browse by topic ---------------------------------------------
          The cards ARE the navigation, and they replaced a row of pills. Same
          state, same behaviour, and they carry what a pill cannot: the icon and
          the one line saying what is inside. Kept on screen while searching,
          with nothing lit, because `search` above clears the pick — so they can
          never be quietly filtering something the search is ignoring. */}
      <section className="pf-about-band">
        <div className="pf-about-wrap">
          <div className="pf-about-cards">
            {ALL_SECTIONS.map((s) => (
              <TopicCard
                key={s.id}
                id={s.id}
                title={s.short ?? s.title}
                blurb={s.blurb}
                icon={s.icon}
                meta={count(s.entries.length, "answer")}
                on={pick === s.id}
                onPick={() => setPick(pick === s.id ? null : s.id)}
              />
            ))}
            <TopicCard
              id={WHATS_NEW}
              title="What’s new"
              blurb="Changes to the site, most recent first."
              icon={faBullhorn}
              meta={count(RELEASES.length, "update")}
              on={pick === WHATS_NEW}
              onPick={() => setPick(pick === WHATS_NEW ? null : WHATS_NEW)}
            />
          </div>

          {searching ? (
            <p className="pf-about-results" role="status">
              {hits === 0 ? "Nothing matches" : count(hits, "answer")} for “{query.trim()}”
            </p>
          ) : pick === null ? null : (
            <div className="pf-about-results">
              <button type="button" onClick={() => setPick(null)} className="pf-backlink">
                <Icon icon={faArrowLeft} /> Show everything
              </button>
              <span className="pf-about-results__what">
                {picked === null ? "What’s new" : picked.title}
              </span>
            </div>
          )}
        </div>
      </section>

      {shown.length === 0 && !showReleases ? (
        <section className="pf-about-band">
          <div className="pf-about-wrap">
            <EmptyState>
              Nothing on this page matches “{query.trim()}”. Try a plainer word — “notes”, “audio”,
              “access”.
            </EmptyState>
          </div>
        </section>
      ) : null}

      {shown.map((s, i) => (
        <SectionBand key={s.id} section={s} openAll={searching} tinted={i % 2 === 1} />
      ))}

      {showReleases ? <Releases tinted={shown.length % 2 === 1} /> : null}

      <section className="pf-about-band pf-about-band--close">
        <div className="pf-about-wrap pf-about-close">
          <h2 className="pf-about-close__title">Anything missing?</h2>
          <p className="pf-about-close__text">
            Something not working, a name spelt wrong, or a book you would like to read — tell
            Asif. This page is kept up to date as the site changes.
          </p>
        </div>
      </section>
    </AppShell>
  );
}

/**
 * One category, as a card.
 *
 * A button rather than a link. It narrows the page in place, so `aria-pressed`
 * says what it is; an anchor would promise a destination and a URL that this page
 * does not have.
 *
 * NAMED by its title alone, and DESCRIBED by its blurb. The whole card is the
 * button, so without this its accessible name is everything inside it — the
 * control sweep read one back as "ReadingEvery book is a modern English edition
 * you can set to your own eyes.3 answers", which is what a screen reader would
 * announce for a press. `aria-describedby` keeps the blurb available rather than
 * hiding it: it follows the name instead of being it.
 */
function TopicCard({
  id,
  title,
  blurb,
  icon,
  meta,
  on,
  onPick,
}: {
  id: string;
  title: string;
  blurb: string;
  icon: Section["icon"];
  meta: string;
  on: boolean;
  onPick: () => void;
}) {
  const said = `${id}-blurb`;

  return (
    <button
      type="button"
      onClick={onPick}
      aria-pressed={on}
      aria-label={title}
      aria-describedby={said}
      className="pf-about-card"
    >
      <span className="pf-about-card__tile" aria-hidden="true">
        <Icon icon={icon} />
      </span>
      <span className="pf-about-card__body">
        <span className="pf-about-card__title">{title}</span>
        <span id={said} className="pf-about-card__blurb">
          {blurb}
        </span>
        <span className="pf-about-card__meta">{meta}</span>
      </span>
    </button>
  );
}

/** One category's questions, as a full-width band. */
function SectionBand({
  section,
  openAll,
  tinted,
}: {
  section: Section;
  openAll: boolean;
  /** Alternating surfaces, so a long page reads as parts rather than as a scroll. */
  tinted: boolean;
}) {
  return (
    <section
      id={section.id}
      className={`pf-about-band${tinted ? " pf-about-band--tint" : ""}`}
      aria-labelledby={`${section.id}-h`}
    >
      <div className="pf-about-wrap">
        <header className="pf-about-lede">
          <h2 id={`${section.id}-h`} className="pf-about-lede__title">
            <Icon icon={section.icon} />
            {section.title}
          </h2>
          <p className="pf-about-lede__blurb">{section.blurb}</p>
        </header>

        <div className="pf-about-qa">
          {section.entries.map((entry) => (
            // `open` is set only while searching, so a match is never hidden
            // behind a closed row. Clearing the search removes the attribute and
            // everything collapses — which is right: the reader is back to
            // skimming. Outside a search the prop never changes, so rows opened
            // by hand stay open.
            //
            // No `name` attribute: that would make these mutually exclusive, and
            // comparing two answers is most of what a page like this is for.
            <details key={entry.q} open={openAll || undefined} className="pf-about-entry">
              <summary className="pf-about-entry__q">{entry.q}</summary>
              <div className="pf-about-entry__a">
                {entry.a.map((p) => (
                  <p key={p}>{p}</p>
                ))}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/** What has changed lately, newest first. */
function Releases({ tinted }: { tinted: boolean }) {
  return (
    <section
      id={WHATS_NEW}
      className={`pf-about-band${tinted ? " pf-about-band--tint" : ""}`}
      aria-labelledby="whats-new-h"
    >
      <div className="pf-about-wrap">
        <header className="pf-about-lede">
          <h2 id="whats-new-h" className="pf-about-lede__title">
            <Icon icon={faBullhorn} />
            What’s new
          </h2>
          <p className="pf-about-lede__blurb">Changes to the site, most recent first.</p>
        </header>

        <ol className="pf-about-timeline">
          {RELEASES.map((release) => (
            <li key={release.date} className="pf-about-moment">
              {/* A machine-readable date beside the one people read. The
                  displayed form is built explicitly rather than by locale, so the
                  server and the browser cannot render it differently and trip
                  hydration. */}
              <time dateTime={release.date} className="pf-about-moment__when">
                {longDate(release.date)}
              </time>
              <ul className="pf-about-moment__what">
                {release.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** `2026-08-05` → `5 August 2026`, without asking the platform for a locale. */
function longDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${d} ${MONTHS[m - 1]} ${y}`;
}
