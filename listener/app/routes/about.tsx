import { useMemo, useState } from "react";
import { faBullhorn } from "@fortawesome/free-solid-svg-icons";

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

export default function About({ loaderData }: Route.ComponentProps) {
  const [query, setQuery] = useState("");
  /** `null` is "everything", which is also what searching forces. */
  const [pick, setPick] = useState<string | null>(null);

  const needle = query.trim().toLowerCase();
  const searching = needle !== "";

  /**
   * What to draw, as sections with only their matching entries.
   *
   * Searching IGNORES the chosen category, deliberately. A reader who types
   * "highlight" while Listening is selected and gets nothing has been told, quite
   * wrongly, that the site cannot do it — and the chip that caused it is three
   * inches above where they are looking. A search is a question about the whole
   * page.
   */
  const shown = useMemo(() => {
    const scope = searching || pick === null ? ALL_SECTIONS : ALL_SECTIONS.filter((s) => s.id === pick);
    if (!searching) return scope;

    return scope
      .map((s) => ({ ...s, entries: s.entries.filter((e) => haystack(e).includes(needle)) }))
      .filter((s) => s.entries.length > 0);
  }, [needle, searching, pick]);

  const hits = shown.reduce((n, s) => n + s.entries.length, 0);

  // "What's new" is a category like any other to the chips, but it holds dated
  // notes rather than questions, so it is not something the search can match. It
  // is hidden while searching rather than shown empty.
  const showReleases = !searching && (pick === null || pick === "whats-new");

  return (
    <AppShell here="about" isAdmin={loaderData.isAdmin}>
      <header className="pf-about__head">
        <h1 className="pf-about__title">About this library</h1>
        <p className="pf-about__lead">
          Classical works published twice over — as modern English reading editions, and as
          long-form audio drawn from the same source. This page is what the site can do, and the
          questions people ask about it.
        </p>
      </header>

      <div className="pf-about__find">
        {/* The placeholder is short enough to survive a 390px screen. It named
            three example words until the phone shot showed it cut off mid-word
            — a search box reading "try “highlight”, “sign ir" looks like a
            rendering fault on the one control this page most needs trusted. */}
        <SearchBox
          id="about-q"
          label="Search this page"
          placeholder="Search this page"
          size="wide"
          action={{ kind: "filter", value: query, onChange: setQuery }}
        />

        {/* Jump-links AND the filter, as one control. Two would be two answers to
            "which part of this page am I looking at". Hidden away while searching
            for the reason given above the `shown` list — a lit chip that the
            search is ignoring is a control lying about what it is doing. */}
        {searching ? (
          <p className="pf-about__hits" role="status">
            {hits === 0 ? "Nothing matches" : count(hits, "answer")} for “{query.trim()}”
          </p>
        ) : (
          <div role="group" aria-label="Jump to a part of this page" className="pf-filters">
            <Chip label="Everything" on={pick === null} onPick={() => setPick(null)} />
            {ALL_SECTIONS.map((s) => (
              <Chip
                key={s.id}
                label={s.short ?? s.title}
                on={pick === s.id}
                onPick={() => setPick(pick === s.id ? null : s.id)}
              />
            ))}
            <Chip
              label="What’s new"
              on={pick === "whats-new"}
              onPick={() => setPick(pick === "whats-new" ? null : "whats-new")}
            />
          </div>
        )}
      </div>

      {shown.length === 0 && !showReleases ? (
        <EmptyState>
          Nothing on this page matches “{query.trim()}”. Try a plainer word — “notes”, “audio”,
          “access”.
        </EmptyState>
      ) : null}

      {shown.map((s) => (
        <SectionBlock key={s.id} section={s} openAll={searching} />
      ))}

      {showReleases ? <Releases /> : null}

      <p className="pf-about__foot">
        Something missing here, or something not working? Tell Asif — this page is kept up to date
        as the site changes.
      </p>
    </AppShell>
  );
}

/** One category, and the entries under it. */
function SectionBlock({ section, openAll }: { section: Section; openAll: boolean }) {
  return (
    <section id={section.id} className="pf-about__section" aria-labelledby={`${section.id}-h`}>
      <h2 id={`${section.id}-h`} className="pf-about__heading">
        <Icon icon={section.icon} />
        {section.title}
      </h2>
      <p className="pf-about__blurb">{section.blurb}</p>

      <div className="pf-about__entries">
        {section.entries.map((entry) => (
          // `open` is set only while searching, so a match is never hidden behind
          // a closed row. Clearing the search removes the attribute and everything
          // collapses — which is right: the reader is back to skimming. Outside a
          // search the prop never changes, so rows opened by hand stay open.
          //
          // No `name` attribute: that would make these mutually exclusive, and
          // comparing two answers is most of what a page like this is for.
          <details key={entry.q} open={openAll || undefined} className="pf-about__entry">
            <summary className="pf-about__q">{entry.q}</summary>
            <div className="pf-about__a">
              {entry.a.map((p) => (
                <p key={p}>{p}</p>
              ))}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

/** What has changed lately, newest first. */
function Releases() {
  return (
    <section id="whats-new" className="pf-about__section" aria-labelledby="whats-new-h">
      <h2 id="whats-new-h" className="pf-about__heading">
        <Icon icon={faBullhorn} />
        What’s new
      </h2>
      <p className="pf-about__blurb">Changes to the site, most recent first.</p>

      <ol className="pf-about__releases">
        {RELEASES.map((release) => (
          <li key={release.date} className="pf-about__release">
            {/* A machine-readable date beside the one people read. The displayed
                form is built explicitly rather than by locale, so the server and
                the browser cannot render it differently and trip hydration. */}
            <time dateTime={release.date} className="pf-about__date">
              {longDate(release.date)}
            </time>
            <ul className="pf-about__changes">
              {release.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * One category chip.
 *
 * `aria-pressed`, not `aria-current`: these do not navigate, they narrow what is
 * on the page. The stylesheet lights both, so a chip looks the same here as it
 * does on the admin screens, where they ARE links.
 */
function Chip({ label, on, onPick }: { label: string; on: boolean; onPick: () => void }) {
  return (
    <button type="button" onClick={onPick} aria-pressed={on} className="pf-filter">
      {label}
    </button>
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
